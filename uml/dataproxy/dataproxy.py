##!/bin/sh -
"exec" "python" "-O" "$0" "$@"

import BaseHTTPServer
import SocketServer
import urllib
import urlparse
import cgi
import signal
import os
import sys
import time
import ConfigParser
import datetime
import optparse
import grp
import pwd
import datalib
import socket
import traceback

import logging
import logging.config
try:
    import cloghandler
except:
    pass

try:
    import json
except:
    import simplejson as json

# note: there is a symlink from /var/www/scraperwiki to the scraperwiki directory
# which allows us to get away with being crap with the paths

configfile = '/var/www/scraperwiki/uml/uml.cfg'
config = ConfigParser.ConfigParser()
config.readfp(open(configfile))

parser = optparse.OptionParser()
parser.add_option("--setuid", action="store_true")
parser.add_option("--pidfile")
parser.add_option("--logfile")
parser.add_option("--toaddrs", default="")
poptions, pargs = parser.parse_args()

class ProxyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    __base         = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle  = __base.handle

    server_version = "DataProxy/ScraperWiki_0.0.1"
    rbufsize       = 0

    def ident(self, params):
        vm_ctr = params.get('uml')
        port = params.get('port')
        
        runID      = None
        short_name = ''

        host = None
        add = None
        try:
            host = config.get("dataproxy", 'lxc_server')
            add  = host[0:host.find(':')]
        except:
            host = None

        self.logger.debug(str({"uml":vm_ctr, "host":host}))
        self.attachauthurl = config.get("dataproxy", 'attachauthurl')

        rem       = self.connection.getpeername()
        loc       = self.connection.getsockname()               
        
        if host and (rem[0].startswith(add) or rem[0].startswith('10.0.1') or vm_ctr == 'lxc'):
            # No need to do the ident, we will return a non-existent runID,short_name for now
            self.logger.debug('We are using LXC so use parameters for ident')
            self.logger.debug( "%s -> %s" % (params.get('vrunid'), params.get("vscrapername",''),) )
            return params.get('vrunid'), params.get("vscrapername", '')            

                # should be using cgi.parse_qs(query) technology here                
        self.logger.debug("LIDENT: %s" % (lident,) )                                
        for line in lident.split('\n'):
            if line:
                key, value = line.split('=',1)
                if key == 'runid':
                    runID = value
                elif key == 'scrapername':
                    short_name = value

        return runID, short_name

    def process(self, db, request):
        self.logger.debug(str(("request", request))[:100])

        sres = ''
        try:
            res = db.process(request)
            sres = json.dumps(res)            
        except Exception, edb:
            self.logger.warning( str(edb) )

        if sres:
            self.logger.debug(sres[:200])
        self.connection.sendall(sres+'\n')
            


        # this morphs into the long running two-way connection
    def do_GET (self) :
        try:
            self.logger = logging.getLogger('dataproxy')

            (scm, netloc, path, params, query, fragment) = urlparse.urlparse(self.path, 'http')
            params = dict(cgi.parse_qsl(query))

            dataauth = None
            attachables = params.get('attachables', '').split()
                    
            firstmessage = {"status":"good"}
            if 'short_name' in params:
                self.attachauthurl = config.get("dataproxy", 'attachauthurl')                
                secure_ips = config.get('dataproxy', 'secure')
                if not self.connection.getpeername()[0] in secure_ips:
                    firstmessage = {"error":"short_name only accepted from secure hosts"}
                else:
                    short_name = params.get('short_name', '')
                    runID = 'fromfrontend.%s.%s' % (short_name, time.time()) 
                    dataauth = "fromfrontend"
            else:
                runID, short_name = self.ident(params)
                if not runID:
                    firstmessage = {"error":"ident failed no runID"}
                elif runID[:8] == "draft|||" and short_name:
                    dataauth = "draft"
                else:
                    dataauth = "writable"

                self.logger.debug( '.%s.' % [short_name])
                    # send back identification so we can compare against it (sometimes it doesn't quite work out)
                firstmessage["short_name"] = short_name
                firstmessage["runID"] = runID
                firstmessage["dataauth"] = dataauth

                # run verification of the names against what we identified
                if runID != params.get('vrunid') or short_name != params.get("vscrapername", ''):
                    self.logger.error("Mismatching scrapername %s" % str([runID, short_name, params.get('vrunid'), params.get("vscrapername", '')]))
                    firstmessage["error"] = "Mismatching scrapername from ident"
                    firstmessage["status"] = "bad: mismatching scrapername from ident"
            
            if path == '' or path is None :
                path = '/'

            if scm not in ['http', 'https'] or fragment:
                firstmessage = {"error":"Malformed URL %s" % self.path}

            # consolidate sending back to trap socket errors
            try:
                self.logger.debug( firstmessage )
                self.connection.sendall(json.dumps(firstmessage)+'\n')
            except socket.error:
                self.logger.warning("connection to dataproxy socket.error: "+str(firstmessage))
            if "error" in firstmessage:
                self.logger.warning("connection to dataproxy refused error: "+str(firstmessage["error"]))
                self.connection.close()
                return
            
            self.logger.debug("connection made to dataproxy for %s %s - %s" % (dataauth, short_name, runID))
            db = datalib.SQLiteDatabase(self, config.get('dataproxy', 'resourcedir'), short_name, dataauth, runID, attachables)

                    # enter the loop that now waits for single requests (delimited by \n) 
                    # and sends back responses through a socket
                    # all with json objects -- until the connection is terminated
            sbuffer = [ ]

            while True:
                try:
                    srec = self.connection.recv(255)
                except socket.error:
                    self.logger.warning("connection to from uml recv error: "+str([runID, short_name]))
                    break
                
                ssrec = srec.split("\n")  # multiple strings if a "\n" exists
                sbuffer.append(ssrec.pop(0))
                while ssrec:
                    line = "".join(sbuffer)
                    if line:
                        try:
                            request = json.loads(line) 
                        except ValueError, ve:
                            # add the content of the line for debugging
                            raise ValueError("%s; reading line '%s'" % (str(ve), line))

                        try:
                            self.process(db, request)
                        except socket.error:
                            self.logger.warning("connection sending to uml socket.error: "+str([runID, short_name]))
                            srec = ""  # break out of loop
                    sbuffer = [ ssrec.pop(0) ]  # next one in
                if not srec:
                    break
            self.logger.debug("ending connection %s - %s" % (short_name, runID))
            self.connection.close()
        except:
            self.logger.error("do_GET uncaught exception: %s" % traceback.format_exc())


    do_HEAD   = do_GET
    do_POST   = do_GET
    do_PUT    = do_GET
    do_DELETE = do_GET


class ProxyHTTPServer(SocketServer.ForkingMixIn, BaseHTTPServer.HTTPServer):
    pass

if __name__ == '__main__':

    # daemon mode
    if os.fork() == 0 :
        os.setsid()
        sys.stdin = open('/dev/null')
        if os.fork() == 0 :
            ppid = os.getppid()
            while ppid != 1 :
                time.sleep(1)
                ppid = os.getppid()
        else :
            os._exit (0)
    else :
        os.wait()
        sys.exit (1)

    pf = open(poptions.pidfile, 'w')
    pf.write('%d\n' % os.getpid())
    pf.close()
        
    if poptions.setuid:
        gid = grp.getgrnam("nogroup").gr_gid
        os.setregid(gid, gid)
        uid = pwd.getpwnam("nobody").pw_uid
        os.setreuid(uid, uid)

    logging.config.fileConfig(configfile)

    port = config.getint('dataproxy', 'port')
    ProxyHandler.protocol_version = "HTTP/1.0"
    httpd = ProxyHTTPServer(('', port), ProxyHandler)
    httpd.max_children = 160
    sa = httpd.socket.getsockname()
    logger = logging.getLogger('dataproxy')
    logger.info(str(("Serving HTTP on", sa[0], "port", sa[1], "...")))
    httpd.serve_forever()

