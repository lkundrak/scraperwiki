"""
Webdatastore.py

"""
from twisted.python import log
from twisted.internet import reactor, protocol
from twisted.protocols import basic
from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.web import server, resource, http

from datalib import SQLiteDatabase

import ConfigParser, logging, cgi
import re, uuid, urlparse
import json, time, sys


class WebDatastoreResource(resource.Resource):
    """
    A web based interface to the datalib that will handle a single request and then
    force the client to reconnect to perform another query.  This will allow us to scale
    across servers once we have sharded the data, and won't tie us into losing multiple 
    connections when the datastore is restarted.
    """
    
    isLeaf=True
    
    
    def _error(self, failure, request ):
        """
        Error handler
        """
        d = defer.Deferred()
        request.notifyFinish().addCallback(self._write, d, {"Error": "There was a problem with the request"} )
    
    
    def _write(self, data, request ):
        """
        Writes the response out to the client by streaming the output rather
        than building it in memory
        """
        log.msg('Writing response')
        request.setResponseCode(http.OK)
        json.dump(data, request)
        request.finish()       


    def check_hash(self, request, name):
        """
        Checks that the X-Scraper-Verified header, added by the HTTPProxy is set
        and matches the hashed name of the scraper.  
        
        If name is not set, then we will allow it through as it will end up with 
        an in-memory database. The hash will still be set in the header but will be 
        just a hash of the shared key so it will be ignored in this case.
        """
        import hashlib
        
        if name == '':
            return True
        
        possibly = hashlib.sha256( '%s%s' % (name, g_secret,) ).hexdigest() 
        header = request.getHeader('X-Scraper-Verified')
        if header is None:
            header = request.args.get('verify', [None])[0]
            
        log.msg( 'Comparing %s == %s' % (possibly, header,) , 
                 logLevel=logging.DEBUG)      
        
        return possibly == header
        

    def process(self, request):
        """
        The main entry point which is run in a separate thread is used to get 
        the arguments and determine the parameters to give to the database.
        
        """
        db = None
        try:
            log.msg( 'Processing request', logLevel=logging.DEBUG )
        
            scrapername = cgi.escape( request.args.get('scrapername', [''])[0] )
            runid = cgi.escape( request.args.get('runid', [''])[0] )            
            command = cgi.escape( request.args.get('command', [''])[0] )         
            attachables = cgi.escape(request.args.get('attachables', [])[0] )
            log.msg('Attachables are : %s' % attachables )
        
            if command == "":
                log.msg(  str(request.args) )
                raise Exception("No command was supplied")
                
            if not self.check_hash(request, scrapername):
                raise Exception("Permission check failed")                
        
            # Work out the appropriate dataauth
            if not runid:
                runid = 'fromfrontend.%s.%s' % (scrapername, time.time(),)                 
                dataauth = "fromfrontend"
            else:
                if runid[:8] == "draft|||" and scrapername:
                    dataauth = "draft"
                else:
                    dataauth = "writable"        
        
            log.msg( "Dataauth for %s is %s" % ( scrapername, dataauth, ))
            
            # Create the database and pass the request to it.
            db = SQLiteDatabase(self, '/var/www/scraperwiki/resourcedir', scrapername, dataauth, runid, attachables)                                
            
            log.msg( "Processing command : %s" % (command,) )
            return db.process(json.loads(command))
        except Exception, e:
            log.err( e )
            return '{"Error": "%s"}' % e.message
        finally:
            if db:
                db.close()


    def render_GET(self, request):
        # For debugging we will have a simple tool
        # TODO: Remove this before production
        return form
                
    def render_POST(self, request):
        self.attachauthurl = attach_auth_url

        log.msg( "Received POST request: %s" % str(request.args))
        
        d = deferToThread( self.process, request)
        d.addCallback(self._write, request)
        d.addErrback(self._error, request)
        return server.NOT_DONE_YET


    
###############################################################################
# Init
###############################################################################
    
# Load the config file from the usual place.
configfile = '/var/www/scraperwiki/uml/uml.cfg'
config = ConfigParser.ConfigParser()
config.readfp(open(configfile))
g_secret = config.get("datarouter", 'proxy_secret')
attach_auth_url = config.get("datarouter", 'attachauthurl')


###############################################################################
# Debug tool
###############################################################################
form = """\
<html><body>
<form action='.' method='POST'>
    <label for='scrapername'>Scraper Name</label>
    <input type='text' name='scrapername' size='30'/><br/>

    <label for='runid'>Run ID</label>
    <input type='text' name='runid' size='30'/><br/>

    <label for='verify'>Verify key</label>
    <input type='text' name='verify' size='30'/><br/>

    
    <label for='command'>Command</label>    
    <textarea name='command' rows='10' cols='30'></textarea><br/>
    <input type='submit' value='send'/>
</form>
</html>\
"""