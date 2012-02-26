"""
Datastore.py

A server that handles incoming connections to various Sqlite databases that 
are stored on disk and accessed over a network. This datastore, like the old 
dataproxy still maintains a connection (per scraper run) and so forces commands 
in sequence.

Things to check/do:
 - Can we better handle huge lines of content?
 - Remove the partial HTTP, either go full HTTP or remove it.
 
"""
from twisted.python import log
from twisted.internet import reactor, protocol
from twisted.protocols import basic
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from datalib import SQLiteDatabase

import ConfigParser, logging
import re, uuid, urlparse
import json, time, sys


###############################################################################
# Classes
###############################################################################


class DatastoreProtocol(basic.LineReceiver):
    """
    Basic LineReceiver implementation (as the protocol is line-at-a-time)
    
    For historical reasons this handles the initial handshake as a HTTP 
    request, and once initiated then treats it like a socket (without any
    headers being sent in the response). Each line received is expected to
    be a JSON string, which is then loaded and processed before returning
    the response, again as a JSON string. Each line sent and received is 
    delimited by \n.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialise the local attributes that we want
        """
        self.have_read_header = False
        self.headers = {}
        self.params = None
        self.action = None
        self.db     = None
        self.short_name, self.dataauth, self.runID, self.attachables = None, None, None, []
        
        
    def db_process_success(self, res):
        """
        Called on a successful database action, the data we are given is encoded and 
        then written as a line.  
        """
        json.dump( res, self.transport )
        self.transport.write('\n')
        

    def db_process_error(self, failure):
        """
        A failed database action. This is likely to be an unhandled exception in
        the datalib so we really should return a valid response.
        """
        log.err( failure )
        self.transport.write('{"error":"Internal Error"}\n')        
        
    
    def write_fail(self, msg='Error'):
        """
        Writes a failure message
        """
        self.transport.write("HTTP/1.1 500 %s\r\n" % msg)
        self.transport.write("Connection: close\r\n")
        self.transport.loseConnection()
        
        
    def process(self, obj):
        """ 
        Process the provided JSON obj (has already been converted to JSON)
        and make sure the response is sent with self.sendLine()
        """
        import hashlib
        
        if self.db is None:
            
            # Check verification key on first run
            print 'Verification key is %s' % self.verification_key
            secret_key = '%s%s' % (self.short_name, self.factory.secret,)
            possibly = hashlib.sha256(secret_key).hexdigest()  
            log.msg( 'Comparing %s == %s' % (possibly, self.verification_key,) , logLevel=logging.DEBUG)      
            if not possibly == self.verification_key:
                # XXX not sure we should log secret
                # log.msg( 'Failed: self.short_name is "%s" self.factory.secret is "%s"' % (self.short_name,self.factory.secret) , logLevel=logging.DEBUG)      
                self.sendLine('{"error": "Permission denied"}')
                return

            self.db = SQLiteDatabase(self, '/var/www/scraperwiki/resourcedir', self.short_name, self.dataauth, self.runID, self.attachables)                        
            
            log.msg( 'Traditional connection, first request', logLevel=logging.DEBUG )
            firstmessage = obj
            firstmessage["short_name"] = self.short_name
            firstmessage["runID"]      = self.runID
            firstmessage["dataauth"]   = self.dataauth
            log.msg( 'Ready to send response of ' + str(firstmessage), logLevel=logging.DEBUG )
            self.sendLine( json.dumps(firstmessage) )
            return
                    
        # We will either get here on the second request of a connected socket because the db
        # will be set, or because the firstmessage wasn't sent so we will process this as part 
        # of the first request
        log.msg( 'Starting async call', logLevel=logging.DEBUG)                                                                     
        d = deferToThread( self.db.process, obj )
        d.addCallback( self.db_process_success )
        d.addErrback( self.db_process_error )
            

    def lineLengthExceeded(self, line):
        """
        When more than 2M is sent, we should let the user know there was a problem
        """
        log.msg('LONGLINE:' + str(self.short_name) )
        self.sendLine(  '{"error": "Buffer size exceeded, please contact feedback@scraperwiki.com if this is causing problems for you"}'  )
        

    def lineReceived(self, line):
        """
        Handles incoming lines of text (correctly separated) these,
        after the http headers will be JSON which expect a JSON response
        """
        # See if we have read all of the HTTP header yet.
        # Store what we need to store for this client 
        # connection
        self.factory.connection_count += 1
        if not self.have_read_header and line.strip() == '':
            self.have_read_header = True
            if not 'X-Scraper-Verified' in self.headers:
                line = '{"status": "good"}'
            log.msg( 'Finished reading headers', logLevel=logging.DEBUG)
                        
        if self.have_read_header:
            try:
                log.msg( 'Starting process message %s' % (line,), logLevel=logging.DEBUG)                                                
                obj = json.loads(line)
                self.process( obj )       
            except Exception, e:
                log.msg('Failed: %s' % (line,))
                log.err(e)
                
        else:
            if self.params is None:
                if not self.parse_params(line):
                    self.sendLine('500 Failed')
                    self.transport.loseConnection()
                    return
            else:
                log.msg( 'Parsing headers: %s' % (line,), logLevel=logging.DEBUG)                
                k,v = line.split(':')
                self.headers[k.strip()] = v.strip()
                log.msg( '%s:%s' % (k,v,) )

            self.verification_key = self.params['verify']

            if 'short_name' in self.params:
                self.attachauthurl = config.get("datarouter", 'attachauthurl')                
                self.short_name = self.params['short_name']
                self.runID = 'fromfrontend.%s.%s' % (self.short_name, time.time()) 
                self.dataauth = "fromfrontend"
            else:
                self.short_name  = self.params['vscrapername']
                self.runID       = self.params['vrunid']
                if self.runID[:8] == "draft|||" and self.short_name:
                    self.dataauth = "draft"
                else:
                    self.dataauth = "writable"
                    
            if 'attachables' in self.params:
                self.attachables = self.params['attachables']
            
            
    def connectionMade(self):
        log.msg( 'Connection made',logLevel=logging.DEBUG)
        self.attachauthurl = attach_auth_url
            
                            
    def connectionLost(self, reason):
        """
        Called when the connection was lost, we should clean up the DB here
        by closing the connection we have to it.
        """
        log.msg( reason )
        log.msg( 'Connection lost',logLevel=logging.DEBUG)
        if self.db:
            self.db.close()
            self.db = None


    def parse_params(self, line):
        """
        Parse the GET request and store the parameters we received.
        """
        log.msg( 'Parsing parameters:%s' % (line,),logLevel=logging.DEBUG)
        self.params = {}        
        m = re.match('(\w+) /(.*) HTTP/(\d+).(\d+)', line)
        if not m:
            log.msg( 'Failed to match url for GET request',logLevel=logging.DEBUG)            
            return
            
        qs = m.groups(0)[1]
        log.msg( qs )
        if '?' in qs:
            self.action = qs[ :qs.find('?') ]            
            qs = qs[ qs.find('?')+1: ]
        else:
            self.action = qs
            qs = None
        log.msg( qs )
        
        if qs:
            self.params.update( dict( [ p.split('=') for p in qs.split('&') ] ) )
            return True
            
        log.msg( 'Failed to parse query string from %s' % (line,),logLevel=logging.DEBUG)            
        return False

    
class DatastoreFactory( protocol.ServerFactory ):
    protocol = DatastoreProtocol
    connection_count = 0
    secret = None
    
    def __init__(self):
        self.secret = config.get("datarouter", 'proxy_secret')
        if not self.secret:
            raise AssertionError('Configuration is incorrect, missing proxy_secret')
    
    
###############################################################################
# Init and run (locally)
###############################################################################
    
# Set the maximum line length and the line delimiter
DatastoreProtocol.delimiter = '\n'
DatastoreProtocol.MAX_LENGTH = 2097152 # HUGE buffer

# Load the config file from the usual place.
configfile = '/var/www/scraperwiki/uml/uml.cfg'
config = ConfigParser.ConfigParser()
config.readfp(open(configfile))
attach_auth_url = config.get("datarouter", 'attachauthurl')

if __name__ == '__main__':
    log.startLogging(sys.stdout)    
    reactor.listenTCP( 10001, DatastoreFactory())
    reactor.run()
