##!/bin/sh -
"exec" "python" "-O" "$0" "$@"

__doc__ = """ScraperWiki FTP Proxy"""

__version__ = "ScraperWiki_0.0.1"

import  sys
import  os
import  socket
import  string
import  urllib
import  urllib2
import  re
import  time
import  signal
import  ConfigParser
import  SocketServer

USAGE       = " [--allowAll] [--varDir=dir] [--subproc] [--daemon] [--config=file]"
child       = None
config      = None
varDir      = '/var'
uid         = None
gid         = None
allowAll    = False
statusLock  = None
statusInfo  = {}
blockmsg    = """500 Scraperwiki has blocked you from accessing "%s" because it is not allowed according to the rules\n"""

class FTPProxyServer (SocketServer.ThreadingMixIn, SocketServer.TCPServer) :

    allow_reuse_address = True

    def __init__ (self, server_address, RequestHandlerClass) :

        SocketServer.TCPServer.__init__ (self, server_address, RequestHandlerClass)


class FTPProxyHandler (SocketServer.BaseRequestHandler) :

    def __init__ (self, request, client_address, server) :

        self.m_allowed = []
        self.m_blocked = []

        self.m_user = None
        self.m_pass = None
        self.m_type = None
        self.m_cwd      = []
        self.m_pasv = None

        SocketServer.BaseRequestHandler.__init__ (self, request, client_address, server)


    def hostAllowed (self, path, scraperID, runID) :

        """
        See if access to a specified host is allowed. These are specified as a list
        of regular expressions stored in a file; the expressions will be anchored at
        both start and finish so they must match the entire host. The file is named
        from the IP address of the caller.

        @type   path     : String
        @param  path     : Hostname
        @type   scraperID: String
        @param  scraperID: Scraper identifier or None
        @return          : True if access is allowed
        """

        import re

        if allowAll :
            return True

        for block in self.m_blocked :
            if re.search(block, path) :
                return False
        for allow in self.m_allowed :
            if re.search(allow, path) :
                return True

        # Temporarily allow all FTP domains
        return True

    def ident (self) :

        """
        Request scraper and run identifiers, and host permissions from the UML.
        This uses local and remote port numbers to identify a TCP/IP connection
        from the scraper running under the controller.
        """

        scraperID = None
        runID     = None

        rem       = self.request.getpeername()
        loc       = self.request.getsockname()
        
        lxc_server = None
        try:
            lxc_server = config.get("ftpproxy", 'lxc_server')
        except:
            pass
                
        port = loc[1]
        ident = ""    
        for attempt in range(5):
            try:
                # If the connection comes form the lxc_server (that we know about from config)
                # then use it.
                if lxc_server and '10.0' in rem[0]:
                    print 'using LXC at ', lxc_server
                    ident_url = 'http://%s:9001/Ident?%s:%s:%s' % (lxc_server, rem[0], rem[1], port)
                    print "Using URL:" + ident_url
                    ident = urllib2.urlopen(ident_url).read()
                    print "Received: _" + ident + "_"
                else:
                    print 'Attempting old-style ident'
                    ident = urllib2.urlopen('http://%s:9001/Ident?%s:%s' % (rem[0], rem[1], port)).read()
                if ident.strip() != "":
                    break
            except:
                pass
                    
        print "IDENT-" + ident + "-"
        for line in string.split (ident, '\n') :
            if line == '' :
                continue
            key, value = string.split (line, '=')
            if key == 'runid' :
                runID     = value
                continue
            if key == 'scraperid' :
                scraperID = value
                continue

        return scraperID, runID

    def notify (self, sending_host, **query) :
        try:
            lxc_server = config.get(varName, 'lxc_server')
        except:
            lxc_server = None
        
        if lxc_server and '10.0' in sending_host:
            host = lxc_server
        else:
            host = sending_host
        
        query['message_type'] = 'sources'
        try    : urllib.urlopen ('http://%s:9001/Notify?%s'% (host, urllib.urlencode(query))).read()
        except : pass

    def handle (self) :

        self.request.send ("220- ScraperWiki FTP Proxy\n")
        self.request.send ("220\n")

        scraperID, runID = self.ident ()

        busy = True
        text = ''
        while busy :

            data = self.request.recv (1024)
            if len(data) == 0 :
                break

            text = text + data
            while text.find ('\n') >= 0 :

                line, text = text.split ('\n', 1)
                line       = line.rstrip()
                args       = line.split (' ',  2)

                print line,args

                if args[0] == 'QUIT' :
                    self.request.send ("221 Toodle-pip.\n")
                    busy = False
                    break

                if args[0] == 'USER' :
                    self.m_user = args[1]
                    self.request.send ("331 Please specify the password.\n")
                    continue

                if args[0] == 'PASS' :
                    self.m_pass = len(args) > 1 and args[1] or ''
                    self.request.send ("230 Login successful.\n")
                    continue

                if args[0] == 'CWD'  :
                    self.m_cwd.append (args[1])
                    self.request.send ("250 Directory successfully changed.\n")
                    continue

                if args[0] == 'TYPE' :
                    self.m_type = args[1]
                    self.request.send ("250 Type set to %s.\n" % args[0])
                    continue

                if args[0] == 'PASV' :
                    print 'Setting up server to listen for response'
                    listen = socket.socket()
                    listen.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listen.bind  ((self.request.getsockname()[0], 0))
                    sockip, sockport   = listen.getsockname()
                    listen.listen(1)
                    print 'Sending 227'                    
                    self.request.send ("227 Entering Passive Mode (%s,%d,%d)\n" % (sockip.replace('.', ','), sockport/256, sockport%256))
                    self.m_pasv = listen.accept()[0]
                    listen.close ()
                    continue

                if args[0] == 'RETR' :

                    url = 'ftp://%s/%s/%s' % (self.m_cwd[2], string.join (self.m_cwd[3:], '/'), args[1])

                    if not self.hostAllowed (url, scraperID, runID) :
                        self.request.send (blockmsg % self.m_cwd[2])
                        continue

                    bytes           = 0
                    failedmessage   = ''
                    self.request.send ("150 File follows.\n")

                    try :
                        data    = urllib2.urlopen(url).read()
                        bytes   = len(data)
                        self.m_pasv.send  (data)
                        self.request.send ("200 OK.\n")
                    except :
                        self.request.send ("500 Transfer failed.\n")
                        failedmessage = "Transfer failed"

                    self.notify \
                        (   self.request.getpeername()[0],
                            runid           = runID,
                            url             = url,
                            failedmessage   = failedmessage,
                            bytes           = len(data),
                            cacheid         = None,
                            cached          = False
                        )

                    self.m_pasv.close()
                    self.m_pasv = None

                    continue

                self.request.send ("500 Unknown command %s.\n" % args[0])
                print "UNKNOWN", args

    def finish (self) :

        pass

def execute (port):

    ftpd  = FTPProxyServer (('', port), FTPProxyHandler)
    sa    = ftpd.socket.getsockname()
    print "Serving FTP on", sa[0], "port", sa[1], "..."

    ftpd.serve_forever()


def sigTerm (signum, frame) :

    try    : os.kill (child, signal.SIGTERM)
    except : pass
    try    : os.remove (varDir + '/run/ftpproxy.pid')
    except : pass
    sys.exit (1)


if __name__ == '__main__' :

    subproc = False
    daemon  = False
    confnam = 'uml.cfg'

    for arg in sys.argv[1:] :

        if arg in ('-h', '--help') :
            print "usage: " + sys.argv[0] + USAGE
            sys.exit (1)

        if arg[: 6] == '--uid=' :
            uid      = arg[ 6:]
            continue

        if arg[: 6] == '--gid=' :
            gid      = arg[ 6:]
            continue

        if arg[ :9] == '--varDir='  :
            varDir  = arg[ 9:]
            continue

        if arg[ :9] == '--config='  :
            confnam = arg[ 9:]
            continue

        if arg == '--allowAll' :
            allowAll = True
            continue

        if arg == '--subproc' :
            subproc = True
            continue

        if arg == '--daemon' :
            daemon = True
            continue

        print "usage: " + sys.argv[0] + USAGE
        sys.exit (1)


    #  If executing in daemon mode then fork and detatch from the
    #  controlling terminal. Basically this is the fork-setsid-fork
    #  sequence.
    #
    if daemon :

        if os.fork() == 0 :
            os .setsid()
            sys.stdin  = open ('/dev/null')
            sys.stdout = open (varDir + '/log/scraperwiki/ftpproxy', 'w', 0)
            sys.stderr = sys.stdout
            if os.fork() == 0 :
                ppid = os.getppid()
                while ppid != 1 :
                    time.sleep (1)
                    ppid = os.getppid()
            else :
                os._exit (0)
        else :
            os.wait()
            sys.exit (1)

        pf = open (varDir + '/run/ftpproxy.pid', 'w')
        pf.write  ('%d\n' % os.getpid())
        pf.close  ()

    if gid is not None : os.setregid (int(gid), int(gid))
    if uid is not None : os.setreuid (int(uid), int(uid))

    #  If running in subproc mode then the server executes as a child
    #  process. The parent simply loops on the death of the child and
    #  recreates it in the event that it croaks.
    #
    if subproc :

        signal.signal (signal.SIGTERM, sigTerm)

        while True :

            child = os.fork()
            if child == 0 :
                break

            sys.stdout.write("Forked subprocess: %d\n" % child)
            sys.stdout.flush()
    
            os.wait()


    config = ConfigParser.ConfigParser()
    config.readfp (open(confnam))

    execute (config.getint ('ftpproxy', 'port'))
