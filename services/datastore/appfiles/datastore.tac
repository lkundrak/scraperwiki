# You can run this .tac file directly with:
#    twistd -ny datastore.tac

"""
This is the tac file for the datastore
"""
from twisted.application import service, internet
from twisted.python.log import ILogObserver, FileLogObserver
from twisted.python.logfile import DailyLogFile
from twisted.web import server, resource

from datastore import DatastoreFactory
from webdatastore import WebDatastoreResource

application = service.Application("datastore")

# attach the service to its parent application
service = service.MultiService()

root = resource.Resource()
root.putChild("", WebDatastoreResource())
internet.TCPServer(20000, server.Site(root)).setServiceParent(application)


dsf = internet.TCPServer(9003, DatastoreFactory()) # create the service
dsf.setServiceParent(service)

service.setServiceParent(application)
