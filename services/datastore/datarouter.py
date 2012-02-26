"""
datarouter.py

A server routes client connections to datastore instances on the same machine (for now)
allowing us to have one per CPU.
 
"""
from twisted.python import log
from twisted.internet import reactor, protocol
from twisted.protocols import basic
from twisted.internet import defer
from twisted.internet.endpoints import TCP4ClientEndpoint

import ConfigParser, logging
import re, uuid, urlparse
import json, time, sys


class ForwardingProtocol(protocol.Protocol):
    """
    The ForwardingProtocol is responsible for forwarding requests on to 
    remote connections, and then streaming back any results to the client
    connected to *this* server.
    """
    
    router = None
    
    def __init__(self):
        pass    
        
        
    def connectionLost(self, reason):
        self.transport.loseConnection()
        if self.router:
            self.router.transport.loseConnection()
                
                                
    def sendMessage(self, msg):
        self.transport.write(msg)
                
                
    def dataReceived(self, data):
        self.router.transport.write( data )
        
        
class ForwardingFactory(protocol.Factory):
    """
    Allows us to create a ForwardingProtocol for connecting to the remote
    datastores and also handling connection failures.
    """
    
    protocol = ForwardingProtocol
        
    def __init__(self, container):
        self.container = container
        
        
    def connectionFailed(self, connector, reason):
        log.msg( 'Connection Failed %s' % reason, logLevel=logging.DEBUG )        
        self.container.instanceConnectionFailed( reason )
        

class DatarouterProtocol(basic.LineReceiver):
    """
    The main protocol used in the router for initiating requests to data stores
    also handling the initial buffer (for when we receive data but are not yet 
    connected to a datastore).
    """
    
    def __init__(self):
        self.connection = None
        self.buffer = ''
        self.error = ''
                        
                        
    def connectionMade(self):
        """
        A new connection is made from a client and so we initiate a new 
        connection a  datastore for this client.
        """
        self.host,self.port = self.factory.choose_instance()
        log.msg( "Instance set to %s:%d" % (self.host, self.port) , 
                 logLevel=logging.DEBUG )

        self.factory = ForwardingFactory(self)
        self.point = TCP4ClientEndpoint(reactor, self.host, self.port)                              
        self.fwd = self.point.connect(self.factory)
        self.fwd.addCallback(self.ready)        
        self.fwd.addErrback( self.notready )


    def notready(self, failure):
        """
        We have received a client connection but failed to connect to the datastore. 
        Currently we are going to show the user an error message, but ideally we'd 
            - Remove the instance from the list
            - Choose another one and only show an error if there are none left.
            - We'd also need to decide how we re-add instances.
        """
        self.error = "The allocated datastore failed to respond"
        
        
    def ready(self, connection):
        """
        We managed to connect to an instance, so we should write everything we 
        have received so far in the initial buffer
        """
        self.connection = connection
        self.connection.router = self
        
        if self.buffer:
            log.msg('Writing initial buffer', logLevel=logging.DEBUG )
            self.connection.transport.write(self.buffer)
        
        
    def lineLengthExceeded(self, line):
        """
        Handle the maximum line length limit being met, and don't even forward the 
        request.
        
        TODO: When more than 262144 bytes is sent, we should let the user know there 
              was a problem.
        TODO: Try and word out how to get the full line (twisted doesn't want us to have it
              by the looks of it).
        """
        self.sendLine(  '{"error": "Buffer size exceeded, please send less data on each request"}'  )
        
        
    def lineReceived(self, line):
        """
        Handles incoming lines of text (correctly separated) these,
        after the http headers will be JSON which expect a JSON response
        
        We need the connection to be available before we can do anything so 
        if it is not then we need to buffer the input
        """
        if self.error:
            self.sendLine(  '{"error": "The allocated datastore failed to respond"}'  )
            self.transport.loseConnection()
            return
            
        log.msg('Received: ' + line, logLevel=logging.DEBUG )
        if not self.connection:
            self.buffer = self.buffer + line + "\n"
            log.msg('Buffered: ' + line, logLevel=logging.DEBUG )                    
        else:        
            self.connection.sendMessage(line + "\n")
            log.msg('Sent: ' + line, logLevel=logging.DEBUG )        
            
            
    def instanceConnectionFailed(self, reason):
        """
        This method will get called when failing to connect to a datastore instance.  Ideally
        in the future we'd like this to pick another instance but that would depend on why the 
        connection failed
        """
        #self.sendLine(  '{"error": "Buffer size exceeded, please send less data on each request"}'  )
        log.msg( 'Connection Failed %s' % reason, logLevel=logging.DEBUG )        
            
            
    def connectionLost(self, reason):
        """
        Called when the connection was lost, we should clean up the DB here
        by closing the connection we have to it.
        """
        if self.connection:
            self.connection.router = None
            self.connection.transport.loseConnection()
            
        log.msg( "Closing connection to %s:%d" % (self.host, self.port) , logLevel=logging.DEBUG )

    
class DatarouterFactory( protocol.ServerFactory ):
    """
    This factory allows us to create an instance of a DataRouter which will 
    route incoming requests to a datastore instance.  This class will also 
    provide the means by which a server can determine which datastore to 
    connect to.
    """
    
    protocol = DatarouterProtocol
    
    instances = []
    http_instances = []
    last_used, last_used_http = 0, 0
    

    def __init__(self, is_http=False):
        self.instances = None
        self.is_http = is_http
        if not is_http:
            DatarouterProtocol.delimiter = '\n'
    
    
    def set_instances(self):
        self.instances = []
        self.http_instances = []
        
        for l in [x.strip() for x in config.get( 'datarouter', 'stores' ).split(',')]:
            h,p = l.split(':')
            self.instances.append( (h,int(p),) )

        for l in [x.strip() for x in config.get( 'datarouter', 'http_stores' ).split(',')]:
            h,p = l.split(':')
            self.http_instances.append( (h,int(p),) )
        

    def choose_instance( self ):
        """
        Does a round robin on all of the instances available and chooses which
        one to use.  We can replace this with something just as naive later on 
        to make sure certain short_names are routed to certain routers. Suggest
        memcached style arrangement (not the crc32(name) modulo solution) - see
        continuum style routing.
        """
        if not self.instances or not self.http_instances:
            self.set_instances()
            
        if self.is_http:
            if self.last_used_http >= len(self.http_instances):
                self.last_used_http = 0
            i = self.http_instances[self.last_used_http]
            self.last_used_http += 1
        else:
            if self.last_used >= len(self.instances):
                self.last_used = 0
            i = self.instances[self.last_used]
            self.last_used += 1
            
        return i
    
    
###############################################################################
# Init and run (locally)
###############################################################################
    
# Set the maximum line length and the line delimiter
DatarouterProtocol.MAX_LENGTH = 262144 # HUGE buffer

# Load the config file from the usual place.
configfile = '/var/www/scraperwiki/uml/uml.cfg'
config = ConfigParser.ConfigParser()
config.readfp(open(configfile))

if __name__ == '__main__':
    log.startLogging(sys.stdout)    
    reactor.listenTCP( 9003, DatarouterFactory(is_http=False))
    reactor.listenTCP( 80, DatarouterFactory(is_http=True))    
    reactor.run()