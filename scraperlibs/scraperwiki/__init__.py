try    : import json
except : import simplejson as json


logfd = None   # set to os.fdopen(3, 'w', 0) for consuming json objects

def dumpMessage(d):
    logfd.write(json.dumps(d) + '\n')
    logfd.flush()


from utils import log, scrape, pdftoxml, swimport
import geo
import datastore
import sqlite
import metadata
import stacktrace

