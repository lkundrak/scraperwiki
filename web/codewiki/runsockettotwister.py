from django.conf import settings
from codewiki import models
import frontend
import urllib
import re
import base64
import cgi
import ConfigParser
import socket

try:                import json
except ImportError: import simplejson as json

config = ConfigParser.ConfigParser()
config.readfp(open(settings.CONFIGFILE))


class RunnerSocket:
    def __init__(self):
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.jsonsbuffer = [ ]
        self.jsonoutputlist = [ ]
        
        self.soc.connect(("127.0.0.1", config.getint("twister", "port")))
        
            # not used
    def runscraper(self, scraper, rev, query_string):
        data = { "command":'connection_open', "guid":scraper.guid, 
                 "username":"DJANGOFRONTEND", "userrealname":"DJANGOFRONTEND", 
                 "language":scraper.language, "scrapername":scraper.short_name, 
                 "isstaff":True, "django_key":config.get('twister', 'djangokey') }
        
        self.soc.send(json.dumps(data)+"\r\n") 
        jdata = self.next()
        cdata = json.loads(jdata)
        #return json.loads(jdata)
        assert cdata["message_type"] == "editorstatus"
        print "loggedineditors ", cdata["loggedineditors"]

        rdata = { "command":"run", "guid":scraper.guid, 
                  "username":"DJANGOFRONTEND", "userrealname":"DJANGOFRONTEND", 
                  "language":scraper.language, "scrapername":scraper.short_name, 
                  "code":scraper.saved_code(rev), "urlquery":query_string 
                }
        self.soc.send(json.dumps(rdata)+"\r\n") 

    # rpc call of a view from the browser
    def runview(self, user, scraper, rev, query_string):
        data = { "command":'rpcrun', "guid":scraper.guid, "username":user.username, 
                 "language":scraper.language, "scrapername":scraper.short_name }
        data["django_key"] = config.get('twister', 'djangokey')
        status = scraper.get_vcs_status(-1)
        data["code"] = status["code"]
        data["rev"] = status.get("prevcommit", {}).get("rev", -1)
        data["attachables"] = [ ascraper.short_name  for ascraper in scraper.attachable_scraperdatabases() ]

        # pass in what we get from the request and ignore the description_envvars
        lqs = scraper.description_envvars().get("QUERY_STRING", "")
        if lqs and query_string:
            data["urlquery"] = "%s&%s" % (lqs, query_string)
        elif lqs:
            data["urlquery"] = lqs
        elif query_string:
            data["urlquery"] = query_string
        

        owners = scraper.userrolemap()["owner"]
        if owners:
            try:
                profile = owners[0].get_profile()
                ownername = profile.name
                data['beta_user'] = profile.beta_user   # to enable certain scrapers to go through the lxc process
            except frontend.models.UserProfile.DoesNotExist:
                data['beta_user'] = False

        try:
            data['userrealname'] = user.get_profile().name
        except frontend.models.UserProfile.DoesNotExist:
            data['userrealname'] = user.username
        except AttributeError:
            data['userrealname'] = user.username
        self.soc.send(json.dumps(data)+"\r\n") 


    def stimulate_run_from_editor(self, scraper, user, clientnumber, language, code, rev, query_string):
        data = { "command":'stimulate_run', "language":language, "code":code, "rev":rev, 
                 "username":user.username, "scrapername":scraper.short_name, "clientnumber":clientnumber, "guid":scraper.guid }
        data["attachables"] = [ ascraper.short_name  for ascraper in scraper.attachable_scraperdatabases() ]

        # pass in what we get from the request and ignore the description_envvars
        lqs = scraper.description_envvars().get("QUERY_STRING", "")
        if lqs and query_string:
            data["urlquery"] = "%s&%s" % (lqs, query_string)
        elif lqs:
            data["urlquery"] = lqs
        elif query_string:
            data["urlquery"] = query_string
        
        try:
            profile = user.get_profile()
            data['beta_user'] = profile.beta_user
        except frontend.models.UserProfile.DoesNotExist:
            data['beta_user'] = False
            
        data["django_key"] = config.get('twister', 'djangokey')

        self.soc.send(json.dumps(data)+"\r\n") 
        jdata = self.readline()
        self.soc.close()
        if not jdata:
            return { "error":"blank stimulation response" }
        cdata = json.loads(jdata)
        return cdata


        # incoming messages from twister are delimited by ",\r\n"
    def next(self):
        while not self.jsonoutputlist:
            srecjsons = self.soc.recv(8192)
            if not srecjsons:
                raise StopIteration  # maybe log the leftovers in self.jsonsbuffer
            ssrecjsons = srecjsons.split(",\r\n")
            self.jsonsbuffer.append(ssrecjsons.pop(0))
            while ssrecjsons:
                self.jsonoutputlist.append("".join(self.jsonsbuffer))
                del self.jsonsbuffer[:]
                self.jsonsbuffer.append(ssrecjsons.pop(0))
            
        jdata = self.jsonoutputlist.pop(0)
        try:
            data = json.loads(jdata)
            if not isinstance(data,dict):
                raise TypeError("We only process dict json messages")
        except:
            # If the data is now json we should log it somewhere so that we can work out if it is just 
            return ""
            
        if data.get("message_type") == "executionstatus" and data.get("content") == "runfinished":
            self.soc.close()
            raise StopIteration 
        return jdata

    def __iter__(self):
        return self

    def readline(self):
        try:
            return self.next()
        except StopIteration:
            return ""
        


