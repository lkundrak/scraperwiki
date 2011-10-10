#!/usr/bin/python -W ignore::DeprecationWarning

import  sys
import  os
import  socket
import  signal
import  string
import  time
import  resource
import  urllib2, urllib
import  optparse
import  scraperwiki
import base64

try    : import json
except : import simplejson as json


    # Unfortunately necessary to do this because PYTHONUNBUFFERED=True does nto get good enough results and tends to still concatenate lines when short and rapid
class ConsoleStream:
    def __init__(self, fd):
        self.m_text = ''
        self.m_fd = fd

    def saveunicode(self, text):
        try:    return unicode(text)
        except UnicodeDecodeError:     pass
        try:    return unicode(text, encoding='utf8')
        except UnicodeDecodeError:     pass
        try:    return unicode(text, encoding='latin1')
        except UnicodeDecodeError:     pass
        return unicode(text, errors='replace')
    
    def write(self, text):
        self.m_text += self.saveunicode(text)
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
parser.add_option("--script", metavar="name")    # not the scraper name, this is tmp file name which we load and execute
options, args = parser.parse_args()

##############################################################
# We can replace the parser with a load of the launch.json
# file and assign the variables appropriately
##############################################################
datastore, runid, scrapername, querystring = None, None, None, None

pathname, _ = os.path.split(options.script)
pathname = os.path.join( os.path.abspath(pathname), 'launch.json')
with open(pathname) as f:
    d = json.loads( f.read() )
    datastore   = d['datastore']
    runid       = d['runid']
    scrapername = d['scrapername']
    querystring = d['querystring']
    attachables = d.get('attachables', '')
    webstore_port = d.get('webstore_port', 0)
    
if querystring:
    os.environ['QUERY_STRING'] = querystring
    os.environ['URLQUERY'] = querystring   


host, port = string.split(datastore, ':')

# Added two new arguments as this seems to have changed in scraperlibs
scraperwiki.datastore.create(host, port, scrapername, runid, attachables, webstore_port)

resource.setrlimit(resource.RLIMIT_CPU, (80, 82,))

#  Set up a CPU time limit handler which simply throws a python so it can be handled cleanly before the hard limit is reached
def sigXCPU(signum, frame) :
    raise Exception("ScraperWiki CPU time exceeded")
signal.signal(signal.SIGXCPU, sigXCPU)

code = open(options.script).read()
try:
    import imp
    mod = imp.new_module('scraper')
    exec code.rstrip() + "\n" in mod.__dict__
except Exception, e:
    etb = scraperwiki.stacktrace.getExceptionTraceback(code)  
    assert etb.get('message_type') == 'exception'
    scraperwiki.dumpMessage(etb)
except SystemExit, se:
    sys.stdout.flush()
    sys.stderr.flush()

    # If we do not temporarily yield a slice of the CPU here then the launching 
    # process will not be able to read from stderr before we exit.
    import time 
    time.sleep(0)

    raise se

sys.stdout.flush()
sys.stderr.flush()
