#!/bin/sh -

"exec" "python" "-O" "$0" "$@"

"""
This script is the interface between the UML/firebox set up and the frontend Orbited TCP socket.  

There is one client object (class RunnerProtocol) per editor window
These recieve and send all messages between the browser and the UML
An instance of a scraper running in the UML is spawnRunner

The RunnerFactory organizes lists of these clients and manages their states
There is one UserEditorsOnOneScraper per user per scraper to handle one user opening multiple windows onto the same scraper
There is one EditorsOnOneScraper per scraper which bundles logged in users into a list of UserEditorsOnOneScrapers

"""

import sys
import os
import signal
import time
import ConfigParser
import datetime
import optparse, grp, pwd
import urllib, urlparse
import logging, logging.config

from proxycallbacks import ClientUpdater

try:
    import cloghandler
except:
    pass



parser = optparse.OptionParser()
parser.add_option("--pidfile")
parser.add_option("--config")
parser.add_option("--logfile")
parser.add_option("--setuid", action="store_true")
poptions, pargs = parser.parse_args()

config = ConfigParser.ConfigParser()
config.readfp(open(poptions.config))

    # primarily to pick up syntax errors
stdoutlog = poptions.logfile and open(poptions.logfile+"-stdout", 'a', 0)  

logger = logging.getLogger('twister')

try:    import json
except: import simplejson as json

from twisted.internet import protocol, utils, reactor, task

# for calling back to the scrapers/twister/status
from twisted.web.client import Agent, ResponseDone
from twisted.web.http import PotentialDataLoss
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.internet.defer import succeed, Deferred
from twisted.internet.error import ProcessDone


from twisterscheduledruns import ScheduledRunMessageLoopHandler
from twisterrunner import MakeRunner, jstime, SetControllerHost

SetControllerHost(config)

agent = Agent(reactor)

# There's one of these 'clients' per editor window open.  All connecting to same factory
class RunnerProtocol(protocol.Protocol):  # Question: should this actually be a LineReceiver?

    def __init__(self):
        # Set if a run is currently taking place, to make sure we don't run 
        # more than one scraper at a time.
        self.processrunning = None
        self.guid = ""
        self.scrapername = ""
        self.isstaff = False
        self.username = ""
        self.userrealname = ""
        self.chatname = ""
        self.cchatname = ""            # combined real/chatname version delimited with | for sending to umlmonitor
        self.clientnumber = -1         # number for whole operation of twisted
        self.clientsessionbegan = datetime.datetime.now()
        self.clientlasttouch = self.clientsessionbegan
        self.guidclienteditors = None  # the EditorsOnOneScraper object
        self.automode = 'autosave'     # autosave, autoload, or draft when guid is not set

        self.clienttype = None # 'editing', 'umlmonitoring', 'rpcrunning', 'scheduledrun', 'stimulate_run', 'httpget'
        

    def connectionMade(self):
        logger.info("connection client# %d" % self.factory.clientcount)
        
        # this returns localhost and is unable to distinguish between orbited or django source
        #socket = self.transport.getHandle()
        #self.logger.info("socket  %s %s" % (socket.getpeername(), type(socket.getpeername())))
        
        self.factory.clientConnectionMade(self)
            # we don't know what scraper they've opened until information is send with first clientcommmand
    
    # message from the clientclientsessionbegan via dataReceived
    def lconnectionopen(self, parsed_data):
        self.guid = parsed_data.get('guid', '')
        self.username = parsed_data.get('username', '')
        self.userrealname = parsed_data.get('userrealname', self.username)
        self.scrapername = parsed_data.get('scrapername', '')
        self.scraperlanguage = parsed_data.get('language', '')
        self.isstaff = (parsed_data.get('isstaff') == "yes")

        if parsed_data.get('umlmonitoring') == "yes":
            self.clienttype = "umlmonitoring"
        else:
            self.clienttype = "editing"

        self.savecode_authorized = (parsed_data.get('savecode_authorized') == "yes")
        self.originalrev = parsed_data.get('originalrev', '')
        
        logger.info("connection open %s: %s %s client# %d" % (self.clienttype, self.cchatname, self.scrapername, self.clientnumber)) 
            # this will cause a notifyEditorClients to be called for everyone on this scraper
        self.factory.clientConnectionRegistered(self)  


    def connectionLost(self, reason):
        if self.clienttype == "editing":
            if self.processrunning:
                self.kill_run(reason='connection lost')
            logger.info("connection lost: %s %s client# %d" % (self.cchatname, self.scrapername, self.clientnumber))
        self.factory.clientConnectionLost(self)


    # this will generalize to making status and other outputs from here
    def handlehttpgetcase(self, line):
        if line:
            self.httpheaders = line.split(" ", (self.httpheaders and 2 or 1))   # GET query 1.1
            return

        self.transport.write('HTTP/1.0 200 OK\n')  
        self.transport.write('Connection: Close\n')  
        self.transport.write('Pragma: no-cache\n')  
        self.transport.write('Cache-Control: no-cache\n')  
        self.transport.write('Content-Type: text/text\n')  
        self.transport.write('\n')
        self.transport.write('hi there')
        self.transport.write(str(self.httpheaders)+'\n')
        self.transport.loseConnection()



    # messages from the client
    def dataReceived(self, data):
        # chunking has recently become necessary because records (particularly from typing) can get concatenated
        # probably shows we should be using LineReceiver
        for lline in data.split("\r\n"):
            line = lline.strip()
            
            # handle case where we have an http connection rather than plain socket connection
            if not self.clienttype and line[:4] == 'GET ':
                self.clienttype = "httpget"
                self.factory.clientConnectionRegistered(self)
                self.httpheaders = [ ]
                self.handlehttpgetcase(line)
                
            if self.clienttype == "httpget":
                self.handlehttpgetcase(line)
            
            elif line:
                try:
                    parsed_data = json.loads(line)
                except ValueError:
                    logger.warning("Nonparsable command ")
                    logger.info("Bad json parsing: client# %d %s" % (self.clientnumber, str([line[:1000]])))
                    self.writejson({'content':"Command not json parsable:  %s " % line, 'message_type':'console'})
                    continue
                if type(parsed_data) != dict or 'command' not in parsed_data:
                    logger.info("Bad json parsing not dict: client# %d %s" % (self.clientnumber, str([line[:1000]])))
                    self.writejson({'content':"Command not json dict with command:  %s " % line, 'message_type':'console'})
                    continue
                command = parsed_data.get('command')
                self.clientcommand(command, parsed_data)
        
            
    def clientcommand(self, command, parsed_data):
        if command != 'typing':
            logger.debug("command %s client# %d" % (command, self.clientnumber))
        
        # update the lasttouch values on associated aggregations
        if command != 'automode' and self.clienttype == "editing":
            self.clientlasttouch = datetime.datetime.now()
            if self.guid and self.username:
                assert self.username in self.guidclienteditors.usereditormap
                self.guidclienteditors.usereditormap[self.username].userlasttouch = self.clientlasttouch
                self.guidclienteditors.scraperlasttouch = self.clientlasttouch

        # data uploaded when a new connection is made from the editor
        if command == 'connection_open':
            self.lconnectionopen(parsed_data)

                # finds the corresponding client and presses the run button on it
                # receives a single record through the pipeline
        elif command == 'stimulate_run':
            self.clienttype = "stimulate_run"
            self.factory.clientConnectionRegistered(self)  

            scrapername = parsed_data["scrapername"]
            guid = parsed_data["guid"]
            username = parsed_data["username"]
            clientnumber = parsed_data["clientnumber"]

            client = None
            eoos = self.factory.guidclientmap.get(guid)
            if eoos:
                usereditor = eoos.usereditormap.get(username)
                if usereditor:
                    for lclient in usereditor.userclients:
                        if lclient.clientnumber == clientnumber:
                            client = lclient

            if parsed_data.get('django_key') != config.get('twister', 'djangokey'):
                logger.error("djangokey_mismatch")
                self.writejson({'status':'twister djangokey mismatch'})
                if client:
                    client.writejson({"message_type":"console", "content":"twister djangokey mismatch"})  
                    client.writejson({'message_type':'executionstatus', 'content':'runfinished'})
                    client = None
            
            if client:
                logger.info("stimulate on : %s %s client# %d" % (client.cchatname, client.scrapername, client.clientnumber))
                if not client.processrunning:
                    client.runcode(parsed_data)
                    self.writejson({"status":"run started"})  
                else:
                    client.writejson({"message_type":"console", "content":"client already running"})  
                    self.writejson({"status":"client already running"})  
            else:
                parsed_data.pop("code", None)   # shorten the log message
                logger.warning("client not found %s" % parsed_data)
                self.writejson({"status":"client not found"})  

            self.transport.loseConnection()

        elif command == 'rpcrun':
            self.username = parsed_data.get('username', '')
            self.userrealname = parsed_data.get('userrealname', self.username)
            self.scrapername = parsed_data.get('scrapername', '')
            self.scraperlanguage = parsed_data.get('language', '')
            self.guid = parsed_data.get("guid", '')
            if parsed_data.get('django_key') == config.get('twister', 'djangokey'):
                self.clienttype = "rpcrunning"
                logger.info("connection open %s: %s %s client# %d" % (self.clienttype, self.username, self.scrapername, self.clientnumber)) 
                self.factory.clientConnectionRegistered(self)  
                self.runcode(parsed_data)
                    # termination is by the calling function when it receives an executionstatus runfinished message
            else:
                logger.error("djangokey_mismatch")
                self.writejson({'status':'twister djangokey mismatch'})
                self.transport.loseConnection()


        elif command == 'saved':
            line = json.dumps({'message_type' : "saved", 'chatname' : self.chatname})
            otherline = json.dumps({'message_type' : "othersaved", 'chatname' : self.chatname})
            self.guidclienteditors.rev = parsed_data["rev"]
            self.guidclienteditors.chainpatchnumber = 0
            self.writeall(line, otherline)
            self.factory.notifyMonitoringClientsSmallmessage(self, "savenote")


    # should record the rev and chainpatchnumber so when we join to this scraper we know
        elif command == 'typing':
            logger.debug("command %s client# %d insertlinenumber %s" % (command, self.clientnumber, parsed_data.get("insertlinenumber")))
            jline = {'message_type' : "typing", 'content' : "%s typing" % self.chatname}
            jotherline = parsed_data.copy()
            jotherline.pop("command")
            jotherline["message_type"] = "othertyping"
            jotherline["content"] = jline["content"]
            self.guidclienteditors.chainpatchnumber = parsed_data.get("chainpatchnumber")
            self.writeall(json.dumps(jline), json.dumps(jotherline))
            self.factory.notifyMonitoringClientsSmallmessage(self, "typingnote")
            
        elif command == 'run':
            if self.processrunning:
                self.writejson({'content':"Already running! (shouldn't happen)", 'message_type':'console'}); 
                return 
            if self.username:
                if self.automode == 'autoload':
                    self.writejson({'content':"Not supposed to run! "+self.automode, 'message_type':'console'}); 
                    return 
            
            if parsed_data.get('guid'):
                self.writejson({'content':"scraper run can only be done through stimulate_run method", 'message_type':'console'}); 
                return 

            logger.info("about to run code %s" % str(parsed_data)[:100])
            self.runcode(parsed_data)
        
        elif command == "umlcontrol":
                # allows monitoring client to remotely kill processes
            if self.clienttype != "umlmonitoring":
                logger.error("umlcontrol called by non-monitoring client")
                return
                
            logger.info("umlcontrol %s" % ([parsed_data]))

            subcommand = parsed_data.get("subcommand")
            if subcommand == "killscraper":
                scrapername = parsed_data["scrapername"]
                for eoos in self.factory.guidclientmap.values():   # would be better if it was by scrapername instead of guid
                    if eoos.scrapername == scrapername:
                        for usereditor in eoos.usereditormap.values():
                            for uclient in usereditor.userclients:
                                if uclient.processrunning:
                                    logger.info("umlcontrol killing run on client# %d %s" % (uclient.clientnumber, scrapername))
                                    uclient.kill_run()

            if subcommand == "killallscheduled":
                for client in self.factory.scheduledrunners.values():
                    if client.processrunning:
                       logger.info("umlcontrol killing run on client# %d %s" % (client.clientnumber, client.scrapername))
                       client.kill_run()
                    else:
                        logger.info("umlcontrol client# %d %s wasn't running" % (client.clientnumber, client.scrapername))
                       
            if "maxscheduledscrapers" in parsed_data:
                self.factory.maxscheduledscrapers = parsed_data["maxscheduledscrapers"]
                self.factory.notifyMonitoringClients(None)

        elif command == "kill":
            if self.processrunning:
                self.kill_run()
                
                # allows the killing of a process in another open window by same user
            elif self.username and self.guid:   
                usereditor = self.guidclienteditors.usereditormap[self.username]
                for client in usereditor.userclients:
                    if client.processrunning:
                        client.kill_run()

        elif command == 'chat':
            line = json.dumps({'message_type':'chat', 'chatname':self.chatname, 'message':parsed_data.get('text'), 'nowtime':jstime(datetime.datetime.now()) })
            self.writeall(line)
        
        elif command == 'requesteditcontrol':
            for usereditor in self.guidclienteditors.usereditormap.values():
                for client in usereditor.userclients:
                    if client.automode == 'autosave':
                        client.writejson({'message_type':'requestededitcontrol', "username":self.username})
        
        elif command == 'giveselrange':
            self.writeall(None, json.dumps({'message_type':'giveselrange', 'selrange':parsed_data.get('selrange'), 'chatname':self.chatname }))
            
        
        elif command == 'automode':
            automode = parsed_data.get('automode')
            if automode == self.automode:
                return

            if not self.username:
                self.automode = automode
                self.factory.notifyMonitoringClients(self)
                return

            usereditor = self.guidclienteditors.usereditormap[self.username]
 
                # self-demote to autoload mode while choosing to promote a particular person to editing mode
            if automode == 'autoload':
                selectednexteditor = parsed_data.get('selectednexteditor')
                if selectednexteditor and selectednexteditor in self.guidclienteditors.usereditormap:
                    assert self.guidclienteditors.usereditormap[selectednexteditor].usersessionpriority >= usereditor.usersessionpriority
                    self.guidclienteditors.usereditormap[selectednexteditor].usersessionpriority = usereditor.usersessionpriority
                usereditor.usersessionpriority = self.guidclienteditors.usersessionprioritynext
                self.guidclienteditors.usersessionprioritynext += 1
            
            self.automode = automode
            
            self.guidclienteditors.notifyEditorClients("")
            self.factory.notifyMonitoringClients(self)

        # this message helps kill it better and killing it from the browser end
        elif command == 'loseconnection':
            # Suspect it is possible in some cases that the client sends this command, and before
            # we have had a chance to close the connection from here, the client has already gone.
            # To cover this case let's handle the exception here and log that loseConnection failed
            try:
                self.transport.loseConnection()
            except: 
                logger.debug('Closing connection on already closed connection failed')
    
    # message to the client
    def writeline(self, line):
        if self.clienttype != "scheduledrun":
            self.transport.write(line+",\r\n")  # note the comma added to the end for json parsing when strung together
        else:
            self.scheduledrunmessageloophandler.receiveline(line)
            
    def writejson(self, data):
        self.writeline(json.dumps(data))

    def writeall(self, line, otherline=""):
        if line: 
            self.writeline(line)  
        
        if self.guidclienteditors:
            if not otherline:
                otherline = line
            
            for client in self.guidclienteditors.anonymouseditors:
                if client != self:
                    client.writeline(otherline); 
            
            for usereditor in self.guidclienteditors.usereditormap.values():
                for client in usereditor.userclients:
                    if client != self:
                        client.writeline(otherline); 
        else:
            assert not self.guid
            
            
    def kill_run(self, reason=''):
        msg = 'Script cancelled'
        if reason:
            msg = "%s (%s)" % (msg, reason)
        self.writeall(json.dumps({'message_type':'executionstatus', 'content':'killsignal', 'message':msg}))
        logger.debug(msg)
        if self.processrunning.pid == "NewSpawnRunner":
            logger.debug("LosingConnectionNewWay "+self.processrunning.pid)
            if hasattr(self.processrunning, 'controllerconnection'):
                self.processrunning.controllerconnection.transport.loseConnection()
        else:
            try:      # (should kill using the new dispatcher call)
                os.kill(self.processrunning.pid, signal.SIGKILL)
            except:
                pass

    
            # this more recently can be called from stimulate_run from django (many of these parameters could be in the client)
    def runcode(self, parsed_data):
        code = parsed_data.get('code', '')
        guid = parsed_data.get('guid', '')
        scraperlanguage = parsed_data.get('language', 'python')
        scrapername = parsed_data.get('scrapername', '')
        urlquery = parsed_data.get('urlquery', '')
        username = parsed_data.get('username', '')
        beta_user = parsed_data.get('beta_user', False)
        attachables = parsed_data.get('attachables', [])
        rev = parsed_data.get('rev', '')
        self.processrunning = MakeRunner(scrapername, guid, scraperlanguage, urlquery, username, code, self, logger, beta_user, attachables, rev)
        self.factory.notifyMonitoringClients(self)
        
        
class UserEditorsOnOneScraper:
    def __init__(self, client, lusersessionpriority):
        self.username = client.username 
        self.userclients = [ ]
        self.usersessionbegan = None
        self.usersessionpriority = lusersessionpriority  # list of users on a scraper sorted by this number, and first one in list gets the editorship
        self.userlasttouch = datetime.datetime.now()
        self.AddUserClient(client)
    
    def AddUserClient(self, client):
        assert self.username == client.username
        if not self.userclients:
            assert not self.usersessionbegan
            self.usersessionbegan = client.clientsessionbegan
        self.userclients.append(client)
        
    def RemoveUserClient(self, client):
        assert self.username == client.username
        assert client in self.userclients
        self.userclients.remove(client)
        return len(self.userclients)
        
        
class EditorsOnOneScraper:
    def __init__(self, guid, scrapername, scraperlanguage, originalrev):
        self.guid = guid
        self.scrapername = scrapername
        self.scraperlanguage = scraperlanguage
        self.scrapersessionbegan = None
        self.anonymouseditors = [ ]
        self.scraperlasttouch = datetime.datetime.now()
        self.usereditormap = { }  # maps username to UserEditorsOnOneScraper
        self.usersessionprioritynext = 0
        self.originalrev = originalrev
        self.chainpatchnumber = 0
        
    def AddClient(self, client):
        assert client.guid == self.guid
        
        if not self.anonymouseditors and not self.usereditormap:
            assert not self.scrapersessionbegan
            self.scrapersessionbegan = client.clientsessionbegan

        if client.username:
            if client.username in self.usereditormap:
                self.usereditormap[client.username].AddUserClient(client)
            else:
                self.usereditormap[client.username] = UserEditorsOnOneScraper(client, self.usersessionprioritynext)
                self.usersessionprioritynext += 1
        else:
            self.anonymouseditors.append(client)
        
        client.guidclienteditors = self
        
    def RemoveClient(self, client):
        assert client.guid == self.guid
        assert client.guidclienteditors == self
        client.guidclienteditors = None
        
        if client.username:
            assert client.username in self.usereditormap
            if not self.usereditormap[client.username].RemoveUserClient(client):
                del self.usereditormap[client.username]
        else:
            assert client in self.anonymouseditors
            self.anonymouseditors.remove(client)
        return self.usereditormap or self.anonymouseditors
        
        
    def notifyEditorClients(self, message):
        editorstatusdata = { 'message_type':"editorstatus" }
        
        editorstatusdata["nowtime"] = jstime(datetime.datetime.now())
        editorstatusdata['earliesteditor'] = jstime(self.scrapersessionbegan)
        editorstatusdata["scraperlasttouch"] = jstime(self.scraperlasttouch)
        
                # order by who has first session (and not all draft mode) in order to determin who is the editor
        usereditors = self.usereditormap.values()
        usereditors.sort(key=lambda x: x.usersessionpriority)
        editorstatusdata["loggedinusers"] = [ ]
        editorstatusdata["loggedineditors"] = [ ]
        editorstatusdata["countclients"] = len(self.anonymouseditors)  # so we know what windows are connected to this editor (if any)
        for usereditor in usereditors:
            editorstatusdata["countclients"] += len(usereditor.userclients)
            if usereditor.userclients[-1].savecode_authorized:   # as recorded in last client for this user
                editorstatusdata["loggedineditors"].append(usereditor.username)
            else:
                editorstatusdata["loggedinusers"].append(usereditor.username)
        
        editorstatusdata["nanonymouseditors"] = len(self.anonymouseditors)
        editorstatusdata["message"] = message
        for client in self.anonymouseditors:
            editorstatusdata["chatname"] = client.chatname
            editorstatusdata["clientnumber"] = client.clientnumber
            client.writejson(editorstatusdata); 
        
        for usereditor in self.usereditormap.values():
            for client in usereditor.userclients:
                editorstatusdata["chatname"] = client.chatname
                editorstatusdata["clientnumber"] = client.clientnumber
                client.writejson(editorstatusdata) 
    
    def Dcountclients(self):
        return len(self.anonymouseditors) + sum([len(usereditor.userclients)  for usereditor in self.usereditormap.values()])


class requestoverduescrapersReceiver(protocol.Protocol):
    def __init__(self, finished, factory):
        self.finished = finished
        self.factory = factory
        self.rbuffer = [ ]
        
    def dataReceived(self, bytes):
        self.rbuffer.append(bytes)
        
    def connectionLost(self, reason):
        if reason.type in [ResponseDone, PotentialDataLoss]:
            try:
                jdata = json.loads("".join(self.rbuffer))
                if "language" in jdata:
                    jdata["language"] = jdata["language"].lower()
                self.factory.requestoverduescrapersAction(jdata)
            except ValueError:
                logger.warning("request overdue bad json: "+str(self.rbuffer)[:1000]+" "+str(reason.type))
        else:
            logger.warning("nope "+str([reason.getErrorMessage(), reason.type, self.rbuffer]))
        self.finished.callback(None)

        

class RunnerFactory(protocol.ServerFactory):
    protocol = RunnerProtocol
    
    def __init__(self):
        self.clients = [ ]   # all clients
        self.clientcount = 0
        self.anonymouscount = 1
        self.announcecount = 0
        
        self.connectedclients = [ ]
        self.umlmonitoringclients = [ ]
        self.draftscraperclients = [ ]
        self.rpcrunningclients = [ ]
        self.stimulate_runclients = [ ]
        self.httpgetclients = [ ]

        self.scheduledrunners = { } # maps from short_name to client objects (that are also put into guidclientmap)
        
        self.guidclientmap = { }  # maps from short_name to EditorsOnOneScraper objects

        # Get these settings from config 
        try:
            max_count      = config.getint("twister", "max_scheduled")            
            schedule_check = config.getint("twister", "schedule_check_seconds")                        
        except:
            max_count      = 10
            schedule_check = 30


        self.maxscheduledscrapers = max_count
        self.notifiedmaxscheduledscrapers = self.maxscheduledscrapers

        # set the visible heartbeat going which is used to call back and look up the schedulers
        self.lc = task.LoopingCall(self.requestoverduescrapers)
        self.lc.start(schedule_check)
        
    #
    # system of functions for fetching the overdue scrapers and knocking them out
    #
    def requestoverduescrapers(self):
        logger.info("requestoverduescrapers")
        uget = {"format":"jsondict", "searchquery":"*OVERDUE*", "maxrows":self.maxscheduledscrapers+5}
        url = urlparse.urljoin(config.get("twister", "apiurl"), '/api/1.0/scraper/search')
        logger.info("API URL: " + url + " with params " + urllib.urlencode(uget) )        
        d = agent.request('GET', "%s?%s" % (url, urllib.urlencode(uget)))
        d.addCallbacks(self.requestoverduescrapersResponse, self.requestoverduescrapersFailure)

    def requestoverduescrapersFailure(self, failure):
        logger.info("requestoverduescrapers failure received "+str(failure))

    def requestoverduescrapersResponse(self, response):
        finished = Deferred()
        response.deliverBody(requestoverduescrapersReceiver(finished, self))
        return finished

    def requestoverduescrapersAction(self, overduelist):
        logger.info("overdue "+str([od.get("short_name")  for od in overduelist]))
        while len(self.scheduledrunners) < self.maxscheduledscrapers and overduelist:
            scraperoverdue = overduelist.pop(0)
            scrapername = scraperoverdue["short_name"]
            if scrapername in self.scheduledrunners:
                continue
            
                    # avoids scheduling cases where someone is editing
            guid = scraperoverdue.get('guid', '')
            if guid in self.guidclientmap:
                continue

                # fabricate a new client (not actually connected to a socket or made by the factory)
            sclient = RunnerProtocol()
            sclient.factory = self
            sclient.guid = guid
            sclient.username = '*SCHEDULED*'
            sclient.userrealname = sclient.username
            sclient.scrapername = scrapername
            sclient.clienttype = "scheduledrun"
            sclient.originalrev = scraperoverdue.get('rev', '')
            sclient.savecode_authorized = False
            sclient.scraperlanguage = scraperoverdue.get('language', '')
            code = scraperoverdue.get('code', '')
            urlquery = scraperoverdue.get('envvars', {}).get("QUERY_STRING", "")

            self.clientConnectionMade(sclient)  # allocates the client number
            self.scheduledrunners[scrapername] = sclient
            djangokey = config.get("twister", "djangokey")
            djangourl = config.get("twister", "djangourl")
            sclient.scheduledrunmessageloophandler = ScheduledRunMessageLoopHandler(sclient, logger, djangokey, djangourl, agent)
            self.clientConnectionRegistered(sclient)  

            logger.info("starting off scheduled client: %s %s client# %d" % (sclient.cchatname, sclient.scrapername, sclient.clientnumber)) 
            beta_user = scraperoverdue.get("beta_user", False)
            attachables = scraperoverdue.get('attachables', [])
            sclient.processrunning = MakeRunner(sclient.scrapername, sclient.guid, sclient.scraperlanguage, urlquery, sclient.username, code, sclient, logger, beta_user, attachables, sclient.originalrev)
            self.notifyMonitoringClients(sclient)


    def scheduledruncomplete(self, sclient, processsucceeded):
        logger.debug("scheduledruncomplete %d" % sclient.clientnumber)
        self.clientConnectionLost(sclient)  # not called from connectionList because there is no socket actually associated with this object
        del self.scheduledrunners[sclient.scrapername]
            # do some post-back to a run object connection
# need to then do something special when the process running is complete


    # able to send out just a change for on a particular client in umlstatuschanges, or the full state of what's happening as umlstatusdata if required
    def notifyMonitoringClients(self, cclient):  # cclient is the one whose state has changed (it can be normal editor or a umlmonitoring case)
        Dtclients = len(self.connectedclients) + len(self.rpcrunningclients) + len(self.umlmonitoringclients) + len(self.draftscraperclients) + sum([eoos.Dcountclients()  for eoos in self.guidclientmap.values()])
        if len(self.clients) != Dtclients:
            logger.error("Miscount of clients %d %d" % (len(self.clients), Dtclients))
        
        # both of these are in the same format and read the same, but umlstatuschanges are shorter
        umlstatuschanges = {'message_type':"umlchanges", "nowtime":jstime(datetime.datetime.now()) }; 
        if self.notifiedmaxscheduledscrapers != self.maxscheduledscrapers:
            self.notifiedmaxscheduledscrapers = self.maxscheduledscrapers
            umlstatuschanges["maxscheduledscrapers"] = self.maxscheduledscrapers

        if cclient and cclient.clienttype == "umlmonitoring":
             umlstatusdata = {'message_type':"umlstatus", "nowtime":umlstatuschanges["nowtime"]}
             umlstatusdata["maxscheduledscrapers"] = self.maxscheduledscrapers
        else:
             umlstatusdata = None
        
        # the cchatnames are username|chatname, so the javascript has something to handle for cases of "|Anonymous5" vs "username|username"
        
        # handle updates and changes in the set of clients that have the monitoring window open
        umlmonitoringusers = { }
        for client in self.umlmonitoringclients:
            if client.cchatname in umlmonitoringusers:
                umlmonitoringusers[client.cchatname] = max(client.clientlasttouch, umlmonitoringusers[client.cchatname])
            else:
                umlmonitoringusers[client.cchatname] = client.clientlasttouch

        #umlmonitoringusers = set([ client.cchatname  for client in self.umlmonitoringclients ])
        if umlstatusdata:
            umlstatusdata["umlmonitoringusers"] = [ {"chatname":chatname, "present":True, "lasttouch":jstime(chatnamelasttouch) }  for chatname, chatnamelasttouch in umlmonitoringusers.items() ]
        if cclient and cclient.clienttype == "umlmonitoring":
            umlstatuschanges["umlmonitoringusers"] = [ {"chatname":cclient.cchatname, "present":(cclient.cchatname in umlmonitoringusers), "lasttouch":jstime(cclient.clientlasttouch) } ]

        # rpcrunningclients
        if umlstatusdata:
            umlstatusdata["rpcrunningclients"] = [ {"clientnumber":client.clientnumber, "present":True, "chatname":client.chatname, "scrapername":client.scrapername, "lasttouch":jstime(client.clientlasttouch)}  for client in self.rpcrunningclients ]
        if cclient and cclient.clienttype == "rpcrunning":
            umlstatuschanges["rpcrunningclients"] = [ {"clientnumber":cclient.clientnumber, "present":(cclient in self.rpcrunningclients), "chatname":cclient.cchatname, "scrapername":cclient.scrapername, "lasttouch":jstime(cclient.clientlasttouch) } ]

        # handle draft scraper users and the run states (one for each user, though there may be multiple draft scrapers for them)
        draftscraperusers = { }  # chatname -> running state
        for client in self.draftscraperclients:
            draftscraperusers[client.cchatname] = bool(client.processrunning) or draftscraperusers.get(client.cchatname, False)
        if umlstatusdata:
            umlstatusdata["draftscraperusers"] = [ {"chatname":chatname, "present":True, "running":crunning }  for chatname, crunning in draftscraperusers.items() ]
        if cclient and not cclient.clienttype == "umlmonitoring" and not cclient.guid:
            umlstatuschanges["draftscraperusers"] = [ { "chatname":cclient.cchatname, "present":(cclient.cchatname in draftscraperusers), "running":draftscraperusers.get(cclient.cchatname, False) } ]

        # the complexity here reflects the complexity of the structure.  the running flag could be set on any one of the clients
        def scraperentry(eoos, cclient):  # local function
            scrapereditors = { }   # chatname -> (lasttouch, [clientnumbers])
            running = False        # we could make this an updated member of EditorsOnOneScraper like lasttouch
            
            for usereditor in eoos.usereditormap.values():
                cchatname = usereditor.userclients[0].cchatname
                clientnumbers = [uclient.clientnumber  for uclient in usereditor.userclients]
                scrapereditors[cchatname] = (usereditor.userlasttouch, clientnumbers)
                running = running or max([ bool(uclient.processrunning)  for uclient in usereditor.userclients ])
            
            for uclient in eoos.anonymouseditors:
                scrapereditors[uclient.cchatname] = (uclient.clientlasttouch, [uclient.clientnumber])
            
                # diff mode
            if cclient:
                scraperusercclient = {'chatname':cclient.cchatname, 'userlasttouch':jstime(cclient.clientlasttouch) }
                if cclient.cchatname in scrapereditors:
                    scraperusercclient['present'] = True
                    scraperusercclient['uclients'] = scrapereditors[cclient.cchatname][1]
                else:
                    scraperusercclient['present'] = False
                scraperusers = [ scraperusercclient ]
            else:
                scraperusers = [ {'chatname':cchatname, 'userlasttouch':jstime(ultc[0]), 'uclients':ultc[1], 'present':True }  for cchatname, ultc in scrapereditors.items() ]
            
            return {'scrapername':eoos.scrapername, 'present':True, 'running':running, 'scraperusers':scraperusers, 'scraperlasttouch':jstime(eoos.scraperlasttouch) }
        
        
        if umlstatusdata:
            umlstatusdata["scraperentries"] = [ ]
            for eoos in self.guidclientmap.values():
                umlstatusdata["scraperentries"].append(scraperentry(eoos, None))
                
        if cclient and cclient.clienttype in ["editing", "scheduledrun"] and cclient.guid:
            if cclient.guid in self.guidclientmap:
                umlstatuschanges["scraperentries"] = [ scraperentry(self.guidclientmap[cclient.guid], cclient) ]
            else:
                umlstatuschanges["scraperentries"] = [ { 'scrapername':cclient.scrapername, 'present':False, 'running':False, 'scraperusers':[ ] } ]
        
        # send the status to the target and updates to everyone else who is monitoring
        #print "\numlstatus", umlstatusdata
        
        # new monitoring client
        if cclient and cclient.clienttype == "umlmonitoring":
            cclient.writejson(umlstatusdata) 
        
        # send only updates to current clients
        for client in self.umlmonitoringclients:
            if client != cclient:
                client.writejson(umlstatuschanges) 

    # just a signal sent for the latest event
    def notifyMonitoringClientsSmallmessage(self, cclient, smallmessage):
        if cclient.guid:
            umlsavenotification = {'message_type':smallmessage, "scrapername":cclient.scrapername, "cchatname":cclient.cchatname, "nowtime":jstime(datetime.datetime.now()) }
            for client in self.umlmonitoringclients:
                client.writejson(umlsavenotification) 
            

    def clientConnectionMade(self, client):
        assert client.clienttype == None
        client.clientnumber = self.clientcount
        self.clients.append(client)
        self.connectedclients.append(client)
        self.clientcount += 1
            # next function will be called when some actual data gets sent

    def clientConnectionRegistered(self, client):
        # Can't remove from the list if it isn't in there so we need to check
        try:
            self.connectedclients.remove(client)
        except:
            logging.error('Failed to remove client %s as it is not in the connectedclient list' % client)
            
        if client.username:
            client.chatname = client.userrealname or client.username
        elif client.clienttype == "editing":
            client.chatname = "Anonymous%d" % self.anonymouscount
            self.anonymouscount += 1
        else:
            client.chatname = "Anonymous"
        client.cchatname = "%s|%s" % (client.username, client.chatname)

        assert client.clienttype in ["umlmonitoring", "editing", "rpcrunning", "stimulate_run", "httpget"]
        
        if client.clienttype == "umlmonitoring":
            self.umlmonitoringclients.append(client)
        elif client.clienttype == 'rpcrunning':
            self.rpcrunningclients.append(client)
        elif client.clienttype == 'httpget':
            self.httpgetclients.append(client)
        elif client.clienttype == 'stimulate_run':
            self.stimulate_runclients.append(client)
        elif client.guid:
            if client.guid not in self.guidclientmap:
                self.guidclientmap[client.guid] = EditorsOnOneScraper(client.guid, client.scrapername, client.scraperlanguage, client.originalrev)
            
            if client.username in self.guidclientmap[client.guid].usereditormap:
                message = "%s opens another window" % client.chatname
            else:
                message = "%s enters" % client.chatname
            
            self.guidclientmap[client.guid].AddClient(client)
            self.guidclientmap[client.guid].notifyEditorClients(message)

        
        else:   # draft scraper type (hardcode the output that would have gone with notifyEditorClients
            editorstatusdata = {'message_type':"editorstatus", "loggedineditors":[], "loggedinusers":[], "nanonymouseditors":1, "countclients":1, "chatname":client.chatname, "message":"Draft scraper connection" }
            editorstatusdata["nowtime"] = jstime(datetime.datetime.now())
            editorstatusdata['earliesteditor'] = jstime(client.clientsessionbegan)
            editorstatusdata["scraperlasttouch"] = jstime(client.clientlasttouch)
            editorstatusdata["clientnumber"] = client.clientnumber
            
            client.writejson(editorstatusdata); 
            self.draftscraperclients.append(client)
        
        if client.clienttype in ["umlmonitoring", "editing", "rpcrunning"]:
            self.notifyMonitoringClients(client)
            
    
    def clientConnectionLost(self, client):
        self.clients.remove(client)  # main list
        logger.debug("removing %s client# %d" % (client.clienttype, client.clientnumber))
        
            # connection open but nothing else happened
        if client.clienttype == None:
            self.connectedclients.remove(client)
        
        elif client.clienttype == "stimulate_run":
            if client in self.stimulate_runclients:
                self.stimulate_runclients.remove(client)
            else:
                logger.error("No place to remove stimulate_run client# %d" % client.clientnumber)

        elif client.clienttype == "httpget":
            if client in self.httpgetclients:
                self.httpgetclients.remove(client)
            else:
                logger.error("No place to remove httpget client# %d" % client.clientnumber)

        elif client.clienttype == "umlmonitoring":
            if client in self.umlmonitoringclients:
                self.umlmonitoringclients.remove(client)
            else:
                logger.error("No place to remove umlmonitoring client# %d" % client.clientnumber)

        elif client.clienttype == "rpcrunning":
            if client in self.rpcrunningclients:
                self.rpcrunningclients.remove(client)
            else:
                logger.error("No place to remove rpcrunning client %d" % client.clientnumber)

        elif not client.guid:
            if client in self.draftscraperclients:
                self.draftscraperclients.remove(client)
            else:
                logger.error("No place to remove draftscraper client %d" % client.clientnumber)
            
        elif (client.guid in self.guidclientmap):   
            if not self.guidclientmap[client.guid].RemoveClient(client):
                del self.guidclientmap[client.guid]
            else:
                if client.username in self.guidclientmap[client.guid].usereditormap:
                    message = "%s closes a window" % client.chatname
                else:
                    message = "%s leaves" % client.chatname
                self.guidclientmap[client.guid].notifyEditorClients(message)
        else:
            logger.error("No place to remove client %d" % client.clientnumber)
        
        self.notifyMonitoringClients(client)



def sigTerm(signum, frame):
    os.kill(child, signal.SIGTERM)
    try:
        os.remove(poptions.pidfile)
    except OSError:
        pass  # no such file
    sys.exit (1)



if __name__ == "__main__":
    # daemon mode
    if os.fork() == 0 :
        os.setsid()
        sys.stdin = open('/dev/null')
        if stdoutlog:
            sys.stdout = stdoutlog
            sys.stderr = stdoutlog
        if os.fork() == 0:
            ppid = os.getppid()
            while ppid != 1:
                time.sleep(1)
                ppid = os.getppid()
        else:
            os._exit(0)
    else:
        os.wait()
        sys.exit(1)

    pf = open(poptions.pidfile, 'w')
    pf.write('%d\n' % os.getpid())
    pf.close()

    if poptions.setuid:
        gid = grp.getgrnam("nogroup").gr_gid
        os.setregid(gid, gid)
        uid = pwd.getpwnam("nobody").pw_uid
        os.setreuid(uid, uid)

    logging.config.fileConfig(poptions.config)

    #  subproc mode
    signal.signal(signal.SIGTERM, sigTerm)
    while True:
        child = os.fork()
        if child == 0 :
            time.sleep (1)
            break

        sys.stdout.write("Forked subprocess: %d\n" % child)
        sys.stdout.flush()

        os.wait()


    # http://localhost:9010/update?runid=1234&message={'sources':'somejson}
    runnerfactory = RunnerFactory()
    port = config.getint('twister', 'port')
    reactor.listenTCP(port, runnerfactory)
    logger.info("Twister listening on port %d" % port)
    reactor.run()   # this function never returns
