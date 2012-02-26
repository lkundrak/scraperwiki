#!/usr/bin/env python

import os, sys, cgi, hashlib
import ConfigParser
import datetime, time
import socket
import traceback
import urllib
import traceback
import json, csv
import StringIO

import logging
import logging.config
try:
    import cloghandler
except:
    pass

import datalib



# note: there is a symlink from /var/www/scraperwiki to the scraperwiki directory
# which allows us to get away with being crap with the paths

configfile = '/var/www/scraperwiki/uml/uml.cfg'
config = ConfigParser.ConfigParser()
config.readfp(open(configfile))
dataproxy_secret = config.get('dataproxy', 'dataproxy_secret')
datalib.attachauthurl = config.get("dataproxy", 'attachauthurl')
datalib.resourcedir = config.get('dataproxy', 'resourcedir')

logging.config.fileConfig(configfile)
# port = config.getint('dataproxy', 'port')
logger = logging.getLogger('dataproxy')
logger.info(".............................")
logger.info("Serving twisted dataproxy now")
datalib.logger = logger

from twisted.python import log
from twisted.internet import reactor, protocol, task
from twisted.protocols import basic
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.internet.interfaces import IPullProducer
from twisted.internet.error import ConnectionDone
from zope.interface import implements


allowed_ips = ['127.0.0.1']

nproductionrowbatch = 600

class DataPullProducer(object):
    implements(IPullProducer)

    def __init__(self, client):
        self.client = client
        if self.client.clienttype == 'httpgetprocessing' and self.client.httpgetparams.get("format") == "csv":
            self.csvwriter = csv.writer(self.client.transport, dialect='excel')
        else:
            self.csvwriter = None
        self.producedrows = 0
        self.producedbatches = 0
            
    def firstProduction(self, res):
        self.keys = res.get("keys", [])
        self.format = self.client.httpgetparams.get("format", "jsondict")
        
        if self.csvwriter:
            self.csvwriter.writerow([ k.encode('utf-8')  for k in self.keys ])
        elif self.client.httpgetpath == "/scrapercall" or self.client.clienttype == "dataproxy_socketmode":
            json.dump(res, self.client.transport)
            self.client.transport.write("\n")
        elif self.client.clienttype == "httpgetprocessing":
            if "callback" in self.client.httpgetparams:
                self.client.transport.write("%s(" % self.client.httpgetparams["callback"])
            if self.format == "jsondict":
                self.bfirstdata = True
            elif self.format == "jsonlist":
                self.client.transport.write("{ keys:")
                json.dump(self.keys, self.client.transport)
                self.client.transport.write(", data:")
                self.bfirstdata = True
            elif self.format == "htmltable":
                self.client.transport.write("<table>\n")
        else:
            logger.warning("client#%d unexpected clienttype %s" % (self.client.clientnumber, self.client.clienttype))

# make the client stop producing delay by one call or find why the cutoff

    def resumeProducing(self):
        if not self.client.db:
            logger.warning("client#%d has no db on resumeProducing" % self.client.clientnumber)
            return self.stopProducing()
        rows = self.client.db.FetchRows(nproductionrowbatch)
        bstillproducing = (len(rows) == nproductionrowbatch)
        self.producedrows += len(rows)
        self.producedbatches += 1
        
        logger.debug("client#%d producedrows %d producedbatches %d byte-object %d" % (self.client.clientnumber, self.producedrows, self.producedbatches, sys.getsizeof(rows)))
        if self.csvwriter:
            def stringnot(v):
                if v == None:
                    return ""
                if type(v) == buffer:
                    v = unicode(v)
                if type(v) in [unicode, str]:
                    return v.encode("utf-8")
                return v
            for row in rows:
                self.csvwriter.writerow([ stringnot(v)  for v in row ])
                
        elif self.client.httpgetpath == "/scrapercall" or self.client.clienttype == "dataproxy_socketmode":
            res = { "data":rows, "producedrows":self.producedrows, "producedbatches":self.producedbatches }
                # shouldn't be doing this if progress_ticks!=yes, which will be case with non-python languages for now
            if bstillproducing:
                res["stillproducing"] = "yes"
            json.dump(res, self.client.transport)
            self.client.transport.write("\n")
            
        elif self.client.clienttype == "httpgetprocessing":
            if self.format == "jsondict" or self.format == "jsonlist":
                if self.bfirstdata:
                    self.client.transport.write("[")
                    self.bfirstdata = False
                elif rows:
                    self.client.transport.write(",")
            if self.format == "jsondict":
                self.client.transport.write(",".join(json.dumps(dict(zip(self.keys, row)))  for row in rows))
            elif self.format == "jsonlist":
                self.client.transport.write(",".join(json.dumps(row)  for row in rows))
            elif self.format == "htmltable":
                def sstringnot(v):
                    if v == None:
                        return ""
                    if type(v) == buffer:
                        v = unicode(v)
                    if type(v) in [unicode, str]:
                        return v.encode("utf-8")
                    return str(v)
                for row in rows:
                    self.client.transport.write("<tr><td>%s</td></tr>\n" % "</td><td>".join(sstringnot(v)  for v in row))

        if not bstillproducing:
            if self.client.clienttype == "httpgetprocessing":
                if self.format == "jsondict":
                    self.client.transport.write("]")
                elif self.format == "jsonlist":
                    self.client.transport.write("]}")
                elif self.format == "htmltable":
                    self.client.transport.write("</table>\n")
                if "callback" in self.client.httpgetparams:
                    self.client.transport.write(")")
            #self.client.transport.unregisterProducer()
            self.stopProducing()
            
    def stopProducing(self):
        if self.client.db:
            self.client.db.cstate = ''
        self.client.factory.releasedbprocess(self.client)
        self.client.transport.unregisterProducer()
        if self.client.clienttype == 'httpgetprocessing':
            self.client.transport.loseConnection()



class DatastoreProtocol(protocol.Protocol):

    def __init__(self):
        self.clientnumber = -1         # number for whole operation of twisted
        self.clientsessionbegan = datetime.datetime.now()
        self.sbufferclient = [ ] # incoming messages from the client
        self.datapullproducer = None
        self.Dattached = [ ] # attached function calls (for debug purposes)
        self.clienttype = 'justconstructed'

        self.httpheaders = [ ]
        self.httpgetparams = {}
        self.httpgetpath = ''
        self.httppostbuffer = None
        self.progress_ticks = 'no'

        self.db = None
        self.dbprocessrequest = None


    def connectionMade(self):
        self.clienttype = 'justconnected'
        self.factory.clientConnectionMade(self)
        logger.info("client#%d connection made" % self.clientnumber)
        try:
            socket = self.transport.getHandle()
            if not socket.getpeername()[0] in allowed_ips:
                logger.warning('connection refused from %s' % (socket.getpeername()[0],))                
                self.transport.loseConnection()
                return
        except Exception, e:
            raise e
        
    def connectionLost(self, reason):
        if reason.type  == ConnectionDone and reason.getErrorMessage() == 'Connection was closed cleanly.':
            logger.info("client#%d connection closed cleanly" % (self.clientnumber))
        else:
            logger.warning("client#%d connection lost reason:%s" % (self.clientnumber, str(reason)))
        self.factory.clientConnectionLost(self)
        self.clienttype == 'connectionlost'


    # this will generalize to making status and other outputs from here
    def handlehttpgetresponse(self):
        self.clienttype = 'httpgetprocessing'
        mimetype = "text/plain"
        if self.httpgetpath == "/api":
            mimetype = "%s; charset=utf-8" % {"csv":"text/csv", "htmltable":"text/html"}.get(self.httpgetparams.get("format"), "application/json")
        self.transport.write('HTTP/1.0 200 OK\r\n')  
        self.transport.write('Connection: Close\r\n')  
        self.transport.write('Pragma: no-cache\r\n')  
        self.transport.write('Cache-Control: no-cache\r\n')  
        self.transport.write('Content-Type: %s\r\n' % mimetype)  
        self.transport.write('\r\n')
        
        if self.httpgetpath == "/api" and "name" in self.httpgetparams and "query" in self.httpgetparams:
            self.short_name = self.httpgetparams["name"]
            self.short_name_dbreadonly = True
            self.dbprocessrequest = { "maincommand":"sqliteexecute", "sqlquery":self.httpgetparams["query"], "data":None, "attachlist":[ ]}
            for aattach in self.httpgetparams.get('attach', '').split(";"):
                if aattach:
                    aa = aattach.split(",")
                    self.dbprocessrequest["attachlist"].append({"name":aa[0], "asname":(len(aa) == 2 and aa[1] or None)})
            logger.info("client#%d connection is API query: %s " % (self.clientnumber, self.dbprocessrequest["sqlquery"][:50]))
            self.factory.addwaitingclient(self)
            
        elif self.httpgetpath == "/scrapercall" and "x-scrapername:" in self.httpheadersmap and self.httppostbuffer:
            httppostmap = json.loads(self.httppostbuffer.getvalue())
            self.short_name = httppostmap.get("scrapername")
            self.short_name_dbreadonly = False
            self.progress_ticks = 'yes'
            self.dbprocessrequest = httppostmap
            logger.info("client#%d connection is scrapercall query: %s" % (self.clientnumber, self.dbprocessrequest["sqlquery"][:50]))
            self.factory.addwaitingclient(self)
            
        elif self.httpgetpath == "/status":
            logger.info("client#%d connection is status query" % (self.clientnumber))
            self.transport.write('There are %d clients connected\n' % len(self.factory.clients))
            for client in self.factory.clients:
                self.transport.write("#%d %s " % (client.clientnumber, client.clienttype))
                if client.dbprocessrequest:
                    self.transport.write(" waiting to process %s " % str(client.dbprocessrequest)[:100])
                ldb = client.db
                if ldb:
                    self.transport.write(" %s processing %s attached: %s" % (ldb.cstate, str(ldb.short_name), str(ldb.attached)))
                self.transport.write("\n")
            self.transport.loseConnection()

        else:
            logger.info("client#%d connection is unrecognized; path:%s" % (self.clientnumber, self.httpgetpath))
            self.transport.write('Hello there\n')
            if self.httppostbuffer:
                self.transport.write('received post body size: %d\n' % len(self.httppostbuffer.getvalue()))
            self.transport.loseConnection()
        

    # directly from def do_GET (self) :
    def handlesocketmodefirstmessage(self):
        self.verification_key = self.httpgetparams['verify']

        self.dataauth = None
        self.attachables = self.httpgetparams.get('attachables', '').split()
        self.progress_ticks = self.httpgetparams.get('progress_ticks', 'no')
        
        firstmessage = {"status":"good"}
        if 'short_name' in self.httpgetparams:
            self.short_name = self.httpgetparams.get('short_name', '')
            self.runID = 'fromfrontend.%s.%s' % (self.short_name, time.time()) 
            self.dataauth = "fromfrontend"
        else:
            self.runID, self.short_name = self.httpgetparams.get('vrunid'), self.httpgetparams.get("vscrapername", '')
            if not self.runID:
                firstmessage = {"error":"ident failed no runID"}
            elif self.runID[:8] == "draft|||" and self.short_name:
                self.dataauth = "draft"
            else:
                self.dataauth = "writable"

                # send back identification so we can compare against it (sometimes it doesn't quite work out)
            firstmessage["short_name"] = self.short_name
            firstmessage["runID"] = self.runID
            firstmessage["dataauth"] = self.dataauth

            # run verification of the names against what we identified
            if self.runID != self.httpgetparams.get('vrunid') or self.short_name != self.httpgetparams.get("vscrapername", ''):
                logger.error("Mismatching scrapername %s" % str([self.runID, self.short_name, self.httpgetparams.get('vrunid'), self.httpgetparams.get("vscrapername", '')]))
                firstmessage["error"] = "Mismatching scrapername from ident"
                firstmessage["status"] = "bad: mismatching scrapername from ident"
        
        # Copied from services/datastore/dataproxy.py
        # Check verification key on first run.
        logger.debug('Verification key is %s' % self.verification_key)
        secret_key = '%s%s' % (self.short_name, dataproxy_secret,)
        possibly = hashlib.sha256(secret_key).hexdigest()  
        logger.debug('Comparing %s == %s' % (possibly, self.verification_key) )
        if possibly != self.verification_key:
            firstmessage = {"error": "Permission denied"}

        # consolidate sending back to trap socket errors
        logger.debug(firstmessage)
        self.transport.write(json.dumps(firstmessage)+'\n')
        
        logger.info("client#%d socket connection opened: short_name:%s" % (self.clientnumber, self.short_name))
        self.short_name_dbreadonly = (self.dataauth == "fromfrontend") or (self.dataauth == "draft" and self.short_name)
        self.clienttype = "dataproxy_socketmode"


    # incoming to this connection
    def dataReceived(self, srec):
        #logger.debug("client#%d rec: %s" % (self.clientnumber, str([srec])[:200]))
        self.sbufferclient.append(srec)
        while self.clienttype in ["justconnected", "httpget_headers", "dataproxy_socketmode"]:
            ssrec = self.sbufferclient[-1].split("\n", 1)  # multiple strings if a "\n" exists (\r precedes \n)
            if len(ssrec) == 1:
                return
            self.sbufferclient[-1] = ssrec[0]
            line = "".join(self.sbufferclient)
            self.sbufferclient = [ ssrec[1] ]
            self.lineReceived(line)
            
        if self.clienttype == 'httppostbody':
            while self.sbufferclient:
                self.httppostbuffer.write(self.sbufferclient.pop(0))
            logger.debug("client#%d postbody current length: %d" % (self.clientnumber, self.httppostbuffer.tell()))
            if self.httpgetcontentlength == self.httppostbuffer.tell():
                self.handlehttpgetresponse()
                

    # incoming to this connection
    # even the socket connections from the uml are initialized with a GET line 
    def lineReceived(self, line):
        #logger.debug("client#%d line: %s" % (self.clientnumber, line[:1000]))
        if self.clienttype == 'justconnected':
            if line[:4] == 'GET ' or line[:5] == 'POST ':
                self.clienttype = "httpget_headers"
            else:
                logger.warning("client#%d has connects with starting line: %s" % (self.clientnumber, line[:1000]))
                
        if self.clienttype == "httpget_headers" and line.strip():
            self.httpheaders.append(line.strip().split(" ", (self.httpheaders and 1 or 2)))   # first line is GET /path?query HTTP/1.0
            logger.debug("client#%d header: %s" % (self.clientnumber, str(self.httpheaders[-1])))
            
        elif self.clienttype == "httpget_headers":  # and not line
            logger.info("client#%d finished headers" % (self.clientnumber))
            self.httpgetpath, q, self.httpgetquery = self.httpheaders[0][1].partition("?")
            self.httpgetparams = dict(cgi.parse_qsl(self.httpgetquery))
            self.httpheadersmap = dict((k.lower(), v)  for k, v in self.httpheaders[1:])
            self.httpgetcontentlength = int(self.httpheadersmap.get('content-length:', '0'))
            
            if self.httpheaders[0][0] == 'POST' and self.httpgetcontentlength:
                self.clienttype = "httppostbody"
                logger.debug("client#%d post body length: %d" % (self.clientnumber, self.httpgetcontentlength))
                self.httppostbuffer = StringIO.StringIO()
                    
            elif (self.httpheaders[0][0] == 'GET' and self.httpgetpath == '/' and self.httpgetparams.get("uml") and len(self.httpheaders) == 1):
                self.clienttype = 'dataproxy_socketmode_start'
                self.handlesocketmodefirstmessage()
                
            else:
                self.clienttype = "httpget_response"
                self.handlehttpgetresponse()
               
        # the main request response loop
        elif self.clienttype == "dataproxy_socketmode":
            try:
                request = json.loads(line) 
            except ValueError, ve:
                request = line
            if type(request) != dict:
                self.sendResponse({"error":'request must be dict', "content":str(request)[:200]})
            elif "maincommand" not in request:
                self.sendResponse({"error":'request must contain maincommand', "content":str(request)})
            elif request["maincommand"] == 'sqlitecommand' and request.get("command") == "attach":
                self.Dattached.append(request)
                self.sendResponse({"status":"attach dataproxy request no longer necessary"})
            elif request["maincommand"] == 'sqlitecommand' and request.get("command") == "commit":
                self.sendResponse({"status":"commit not necessary as autocommit is enabled"})
            elif self.db:
                logger.error("client#%d received during deferredrequest: %s" % (self.clientnumber, line[:1000]))
                self.sendResponse({"error":'already doing deferredrequest!!!'})
            elif self.dbprocessrequest:
                self.sendResponse({"error":'already waiting on a processrequest!!!'})
            else:
                self.dbprocessrequest = request
                self.factory.addwaitingclient(self)

        else:
            logger.warning("client#%d Unhandled lineReceived: %s" % (self.clientnumber, line[:1000]))

    def sendResponse(self, res):
        #logger.warning("client#%d %s response: %s" % (self.clientnumber, self.clienttype, str(res)))
        if self.clienttype == "httpgetprocessing":
            if "callback" in self.httpgetparams:
                self.transport.write("%s(" % self.httpgetparams["callback"])
            if "keys" not in res:
                json.dump(res, self.transport)
            elif self.httpgetpath == "/scrapercall":
                json.dump(res, self.transport)
            elif self.httpgetparams.get("format", "jsondict") == "jsondict":
                json.dump([ dict(zip(res["keys"], values))  for values in res["data"] ], self.transport, indent=4)
            elif self.httpgetparams.get("format") == "jsonlist":
                json.dump({"keys":res["keys"], "data":res["data"]}, self.transport)
            elif self.httpgetparams.get("format") in ["csv", "htmltable"]:
                pass
            else:
                self.transport.write("Unknown format: %s" % self.httpgetparams.get("format"))
            if "callback" in self.httpgetparams:
                self.transport.write(")")
            self.transport.loseConnection()
            
        else:
            if "error" in res:
                logger.warning("client#%d error: %s" % (self.clientnumber, str(res)))
            json.dump(res, self.transport)
            self.transport.write('\n')

        
    def db_process_success(self, res):
        logger.info("client#%d completed process: %s" % (self.clientnumber, str(res)[:50]))
        if res.get("stillproducing") == "yes":
            #request["maincommand"] == "sqliteexecute"
            self.db.cstate = "fetchrowsproducing"
            self.datapullproducer = DataPullProducer(self)
            self.datapullproducer.firstProduction(res)
            self.transport.registerProducer(self.datapullproducer, False)  # immediately sets it going
            
        else:
            self.factory.releasedbprocess(self)
            self.sendResponse(res)


        # the error can be called after success has been called by same deferred?  how?
    def db_process_error(self, failure):
        logger.warning("client#%d process failure %s" % (self.clientnumber, str(failure)[:900]))
        self.db_process_success({"error":"dataproxy.process: %s" % str(failure)})


class DatastoreFactory(protocol.ServerFactory):
    protocol = DatastoreProtocol
    
    def __init__(self):
        self.clients = [ ]     # all clients
        self.clientcount = 0   # for clientnumbers
        self.clientswaitingforswconn = [ ]
        
        self.lc = task.LoopingCall(self.processnextwaitingclient)
        self.lc.start(5)

    def addwaitingclient(self, client):
        logger.info("client#%d adding to clientswaitingforswconn" % client.clientnumber)
        assert client not in self.clientswaitingforswconn
        self.clientswaitingforswconn.append(client)
        reactor.callLater(0, self.processnextwaitingclient)

        # this has everything we want about the request so can delay ones that would clash
    def processnextwaitingclient(self):
        logger.debug("looping call %d" % len(self.clientswaitingforswconn))
        if not self.clientswaitingforswconn:
            return
            
        client = self.clientswaitingforswconn.pop(0)
        logger.info("client#%d open process" % client.clientnumber)
        client.db = datalib.SQLiteDatabase(client.short_name, client.short_name_dbreadonly, client.dbprocessrequest.get("attachlist", []))
        client.db.Dclientnumber = client.clientnumber
        
        client.db.clientforresponse = client
        
        d = deferToThread(client.db.process, client.dbprocessrequest)
        client.dbprocessrequest = None
        d.addCallback(client.db_process_success)
        d.addErrback(client.db_process_error)
        
        
    def releasedbprocess(self, client):
        db = client.db
        client.db = None
        if db:
            db.close()
        
    def clientConnectionMade(self, client):
        client.clientnumber = self.clientcount
        self.clients.append(client)
        self.clientcount += 1
        
    def clientConnectionLost(self, client):
        if client.db:
            logger.info("client#%d disconnecting running db" % (client.clientnumber))
            client.db.clientforresponse = None

        if client in self.clients:
            logger.info("client#%d removing" % (client.clientnumber))
            self.clients.remove(client)  # main list
        else:
            logger.error("client#%d not in clientlist!!!" % client.clientnumber)

        