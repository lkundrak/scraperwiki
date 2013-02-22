# You can run this .tac file directly with:
#    twistd -ny dataproxy.tac

"""
This is the tac file for the dataproxy
"""
from twisted.application import service, internet
from twisted.python.log import ILogObserver, FileLogObserver
from twisted.python.logfile import DailyLogFile
from twisted.web import server, resource

from dataproxy import DatastoreFactory

application = service.Application("dataproxy")

# attach the service to its parent application
service = service.MultiService()

dsf = internet.TCPServer(9003, DatastoreFactory()) # create the service
dsf.setServiceParent(service)

service.setServiceParent(application)
