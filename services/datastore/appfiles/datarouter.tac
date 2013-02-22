import resource
from txlb.application import director

configFile = '/var/www/scraperwiki/services/datastore/appfiles/config.xml'
resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
application = director.setup(configFile)