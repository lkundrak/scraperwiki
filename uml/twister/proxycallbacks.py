from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

class ClientUpdater(Resource):
    def render_GET(self, request):
        request.responseHeaders.addRawHeader('Content-Type','application/json')
        request.setResponseCode(200)
        
        runid = request.args.get('runid', None)
        if not runid:
            return "{'status':'bad', 'error': 'No runid'}"
        
        update = request.args.get('message', None)
        if not update:
            return "{'status':'bad', 'error': 'No message'}"
        
        # Do something with the update/runid
        
        
        return "{'status':'ok', 'runid': %s, 'update': %s}" % (runid, update,)

