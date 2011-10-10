import sys

from twisted.web import proxy, http
from twisted.python import log

log.startLogging(sys.stdout)

class ScraperProxyClient(proxy.ProxyClient):

    def handleHeader( self, key, value ):
        proxy.ProxyClient.handleHeader(self, key, value)
        
    def handleResponsePart(self, data):
        proxy.ProxyClient.handleResponsePart(self,data)
        
    def handleResponseEnd(self):
        proxy.ProxyClient.handleResponseEnd(self)
        
        
class ScraperProxyClientFactory(proxy.ProxyClientFactory):
    
    def buildProtocol(self, addr):
        client = proxy.ProxyClientFactory.buildProtocol(self, addr)
        client.__class__ = ScraperProxyClient
        return client


class ScraperProxyRequest(proxy.ProxyRequest):
    protocols = { 'http': ScraperProxyClientFactory }

    def __init__(self, *args):
        proxy.ProxyRequest.__init__(self, *args)
        
    def process(self):
        # TODO Process self.uri to see if we are allowed to access it
        # We probably want to do an ident with the current controller and 
        # probably a notify as well.  Once we know we can carry on then 
        # we should
        proxy.ProxyRequest.process(self)
        
        
class ScraperProxy(proxy.Proxy):
    
    def __init__(self):
        proxy.Proxy.__init__(self)
        
    def requestFactory(self, *args):
        return ScraperProxyRequest(*args)
    
        
class ScraperProxyFactory(http.HTTPFactory):
    
    def __init__(self):
        http.HTTPFactory.__init__(self)
        
    def buildProtocol(self, addr):
        protocol = ScraperProxy()
        return protocol
    
        
if __name__ == '__main__':
    from twisted.internet import reactor
    px = ScraperProxyFactory()
    reactor.listenTCP(9000, px)
    reactor.run()

    
    
    
    
    
    