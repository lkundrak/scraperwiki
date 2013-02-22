#!/usr/bin/python -W ignore::DeprecationWarning

import base64
import optparse
import os
import resource
import signal
import socket
import string
import sys
import time

# ScraperWiki
import scraperwiki

# Local
import swutil

try    : import json
except : import simplejson as json


# Unfortunately necessary to do this because PYTHONUNBUFFERED=True
# does not get good enough results and tends to still concatenate lines
# when short and rapid
class ConsoleStream:
    def __init__(self, fd):
        self.m_text = ''
        self.m_fd = fd

    def write(self, text):
        self.m_text += swutil.as_unicode(text)
        if self.m_text and self.m_text[-1] == '\n' :
            self.flush()

    def flush(self) :
        if self.m_text:
            scraperwiki.dumpMessage({'message_type': 'console', 'content': self.m_text})
            self.m_text = ''
            self.m_fd.flush()
            
    def close(self):
        self.m_fd.close()

    def fileno(self):
        return self.m_fd.fileno()


scraperwiki.logfd = sys.stderr
sys.stdout = ConsoleStream(scraperwiki.logfd)
sys.stderr = ConsoleStream(scraperwiki.logfd)

parser = optparse.OptionParser()
# The script to load and execute (not the scraper name)
parser.add_option("--script", metavar="name")
# The scraper name, visible on command line (good for ps | grep)
# but not otherwise used.
parser.add_option("--scraper", metavar="scraper")
options, args = parser.parse_args()

##############################################################
# We can replace the parser with a load of the launch.json
# file and assign the variables appropriately
##############################################################
datastore, runid, scrapername, querystring = None, None, None, None
http_stores = []
verification_key = None

pathname, _ = os.path.split(options.script)
pathname = os.path.join( os.path.abspath(pathname), 'launch.json')
with open(pathname) as f:
    d = json.loads(f.read())
datastore   = d['datastore']
runid       = d['runid']
scrapername = d['scrapername']
querystring = d['querystring']
attachables = d.get('attachables', '')        
verification_key = d.get('verification_key', '')

if querystring:
    os.environ['QUERY_STRING'] = querystring
    os.environ['URLQUERY'] = querystring   

host, port = string.split(datastore, ':')

# Added two new arguments as this seems to have changed in scraperlibs
scraperwiki.datastore.create(host, port, scrapername, runid,
  attachables, verification_key)


# CPU limits.
resource.setrlimit(resource.RLIMIT_CPU, (160, 162,))
# The CPU time limit handler simply throws a Python exception
# so it can be handled cleanly before the hard limit is reached.
def sigXCPU(signum_, frame_):
    raise scraperwiki.CPUTimeExceededError("ScraperWiki CPU time exceeded")
signal.signal(signal.SIGXCPU, sigXCPU)

with open(options.script) as codef:
    code = codef.read()
try:
    import imp
    mod = imp.new_module('scraper')
    exec code.rstrip() + "\n" in mod.__dict__
except Exception, e:
    etb = swutil.getExceptionTraceback(code)  
    assert etb.get('message_type') == 'exception'
    scraperwiki.dumpMessage(etb)
except SystemExit, se:
    sys.stdout.flush()
    sys.stderr.flush()

    # If we do not temporarily yield a slice of the CPU here then the
    # launching process will not be able to read from stderr before
    # we exit.
    import time 
    time.sleep(0)

    raise se

sys.stdout.flush()
sys.stderr.flush()
