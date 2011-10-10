from twisted.internet.defer import succeed, Deferred
from twisted.internet.error import ProcessDone, ConnectionRefusedError
from twisted.internet import protocol
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss

from zope.interface import implements
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers

import datetime
import urlparse
import urllib

try:    import json
except: import simplejson as json

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

# this is only so we can see what errors (if any) are returning from django (which can be the annoying CRSF blocker)
class updaterunobjectReceiver(protocol.Protocol):
    def __init__(self, finished, logger):
        self.finished = finished
        self.logger = logger
        self.rbuffer = [ ]
        
    def dataReceived(self, bytes):
        self.rbuffer.append(bytes)
        
    def connectionLost(self, reason):
        if reason.type in [ResponseDone, PotentialDataLoss]:
                # sometimes need to print huge amount out to read the html formatted error
            #self.logger.debug("updaterunobject response: %s"% str("".join(self.rbuffer)[:50000]))
            self.logger.debug("updaterunobject response: %s"% str(["".join(self.rbuffer)[:2000]]))
        else:
            self.logger.warning("nope "+str([reason.getErrorMessage(), reason.type, self.rbuffer]))
        self.finished.callback(None)


TAIL_LINES = 5
APPROXLENOUTPUTLIMIT = 3000
temptailmessage = "\n\n[further output lines suppressed]\n"

class ScheduledRunMessageLoopHandler:
    def __init__(self, client, logger, djangokey, djangourl, agent):
        # a partial implementation of editor.js
        self.exceptionmessage = [ ]
        self.completiondata = None
        self.outputmessage = [ ]
        self.domainscrapes = { }  # domain: { "pages_scraped":0, "bytes_scraped":0 }
        self.discarded_lines = 0
        self.discarded_characters = 0

        self.output = ""
        self.run_ended = None

        self.upost = {"django_key":djangokey}
        self.upost["pages_scraped"] = 0
        self.upost["records_produced"] = 0
        self.upost["scrapername"] = client.scrapername
        self.upost["clientnumber"] = client.clientnumber
        
        self.logger = logger
        self.djangourl = djangourl
        self.agent = agent

    def updaterunobjectFailure(self, failure):
        self.logger.info("requestoverduescrapers failure received "+str(failure))
    
    def updaterunobjectResponse(self, response):
        finished = Deferred()
        response.deliverBody(updaterunobjectReceiver(finished, self.logger))
        return finished

    def updaterunobject(self, bfinished):
        url = urlparse.urljoin(self.djangourl, 'scraper-admin/twistermakesrunevent/')
        self.logger.info("attempting to post: "+url)
        self.upost["output"] = self.output
        if bfinished:
            self.upost["exitstatus"] = self.exceptionmessage and 'exceptionmessage' or 'done'
            self.upost["domainscrapes"] = json.dumps(self.domainscrapes)
            if self.exceptionmessage:
                self.upost['exceptionmessage'] = self.exceptionmessage
                
        # urllib.urlencode applies str() to each value in the list, which is dumb.
        # to get a proper error, print some chinese characters
        # need to get an explanation for this design of urlencode
        lupost = self.upost.copy()
        for key in lupost:
            if type(lupost[key]) == unicode:
                lupost[key] = lupost[key].encode("utf8")
        ulupost = urllib.urlencode(lupost)
        
        d = self.agent.request('POST', url, Headers(), StringProducer(ulupost))
        d.addCallbacks(self.updaterunobjectResponse, self.updaterunobjectFailure)
        
    def receiveline(self, line):
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise TypeError('Incorrect type of JSON')
        except Exception, e:
            self.logger.debug( "Failed to json.loads() %s %s" % (str([line]), str(e)))
            return
                    
        message_type = data.get('message_type')
        content = data.get("content")
        if message_type == 'executionstatus':
            if content == "startingrun":
                self.upost["run_id"] = data.get("runID")
                self.output = "%sEXECUTIONSTATUS: uml=%s runid=%s\n" % (self.output, data.get("uml"), data.get("runID"))
            elif content == "runcompleted":
                self.logger.debug( "Got run completed : %s" % (line,)  )                
                self.completiondata = data
                self.completionmessage = '';
                if data.get('elapsed_seconds'):
                    self.completionmessage += str(data.get("elapsed_seconds")) + " seconds elapsed, " 
                if data.get("CPU_seconds", False): # Until we can get CPU used
                    self.completionmessage += str(data.get("CPU_seconds")) + " CPU seconds used";
                if "exit_status" in data and data.get("exit_status") != 0:
                    self.completionmessage += ", exit status " + str(data.get("exit_status"));
                if "term_sig_text" in data:
                    self.completionmessage += ", terminated by " + data.get("term_sig_text");
                elif "term_sig" in data:
                    self.completionmessage += ", terminated by signal " + str(data.get("term_sig"));
                self.logger.debug( "Completion status : %s" % (line,)  )
                
            self.updaterunobject(False)
            
        elif message_type == "sources":
            self.upost["pages_scraped"] += 1  # soon to be deprecated 
            
            url = data.get('url')
            netloc = "%s://%s" % urlparse.urlparse(url)[:2]
            if "first_url_scraped" not in self.upost and url and netloc[-16:] != '.scraperwiki.com' and url[-10:] != 'robots.txt':
                self.upost["first_url_scraped"] = data.get('url')
            if netloc:
                if netloc not in self.domainscrapes:
                    self.domainscrapes[netloc] = { "pages_scraped":0, "bytes_scraped":0 }
                self.domainscrapes[netloc]["pages_scraped"] += 1
                self.domainscrapes[netloc]["bytes_scraped"] += int(data.get('bytes'))
        
        elif message_type == "data":
            self.upost["records_produced"] += 1
        
        elif message_type == "sqlitecall":
            if data.get('insert'):
                self.upost["records_produced"] += 1
        
        elif message_type == "exception":   # only one of these ever
            self.upost["exception_message"] = data.get('exceptiondescription')

            # TODO/TOCONSIDER
            # If this is a specific type of message (such as Python NameError/SyntaxError)
            # we should probably hit a flag to say it should not be scheduled (without changing the 
            # run_interval) and then reset the flag each save. If it is broken why try to run it?
            
            for stackentry in data.get("stackdump"):
                sMessage = stackentry.get('file')
                if sMessage:
                    if sMessage == "<string>":
                        sMessage = "Line %d: %s" % (stackentry.get('linenumber', -1), stackentry.get('linetext'))
                    if stackentry.get('furtherlinetext'):
                        sMessage += " -- " + stackentry.get('furtherlinetext') 
                    self.exceptionmessage.append(sMessage)
                if stackentry.get('duplicates') and stackentry.get('duplicates') > 1:
                    self.exceptionmessage.append("  + %d duplicates" % stackentry.get('duplicates'))
            
            if data.get("blockedurl"):
                self.exceptionmessage.append("Blocked URL: %s" % data.get("blockedurl"))
            self.exceptionmessage.append('')
            self.exceptionmessage.append(data.get('exceptiondescription'))
        
        elif message_type == "console":
            while content:
                self.outputmessage.append(content[:APPROXLENOUTPUTLIMIT])
                content = content[APPROXLENOUTPUTLIMIT:]

        elif message_type == "editorstatus":
            pass
            
        elif message_type == "chat":
            pass

        else:
            self.outputmessage.append("Unknown: %s\n" % line)
            
        
        # live update of event output so we can watch it when debugging scraperwiki platform
        # reduce pressure on the server by only updating when we over-run the buffer
        if self.outputmessage and len(self.output) < APPROXLENOUTPUTLIMIT:
            while self.outputmessage:
                self.output = "%s%s" % (self.output, self.outputmessage.pop(0))
                if len(self.output) >= APPROXLENOUTPUTLIMIT:
                    self.output = "%s%s" % (self.output, temptailmessage)
                    self.updaterunobject(False) 
                    break
            self.run_ended = datetime.datetime.now()
            #self.updaterunobject(False)

        while len(self.outputmessage) >= TAIL_LINES:
            discarded = self.outputmessage.pop(0)
            self.discarded_lines += 1
            self.discarded_characters += len(discarded)


    def schedulecompleted(self):
        # append last few lines of the output
        if self.outputmessage:
            #assert len(event.output) >= APPROXLENOUTPUTLIMIT
            outputtail = [ self.outputmessage.pop() ] 
            while self.outputmessage and len(outputtail) < TAIL_LINES and sum(map(len, outputtail)) < APPROXLENOUTPUTLIMIT:
                outputtail.append(self.outputmessage.pop())
            outputtail.reverse()
                
            omittedmessage = ""
            if self.discarded_lines > 0:
                omittedmessage = "\n    [%d lines, %d characters omitted]\n\n" % (self.discarded_lines, self.discarded_characters)
            self.output = "%s%s%s" % (self.output[:-len(temptailmessage)], omittedmessage, "".join(outputtail))
            

        if self.exceptionmessage:
            self.output = "%s\n\n*** Exception ***\n\n%s\n" % (self.output, "\n\n".join(self.exceptionmessage))
        if self.completiondata:
            self.output = "%s\nEXECUTIONSTATUS: %s\n" % (self.output, self.completionmessage)
        else:
            self.output = "%s\nEXECUTIONSTATUS: [Run was interrupted (possibly by a timeout)]\n" % (self.output)
        
        self.updaterunobject(True)

