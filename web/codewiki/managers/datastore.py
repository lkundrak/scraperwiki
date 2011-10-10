import  settings
import  socket
import  struct
import  urllib

try:
    import json
except: 
    import simplejson as json


class DataStore(object):
    def __init__ (self, short_name) :
        self.sbuffer = [ ] 
        self.m_socket = socket.socket()
        self.m_socket.connect((settings.DATAPROXY_HOST, settings.DATAPROXY_PORT))
        
        # Set receive timeout to be 20 seconds so that this failing doesn't cause us to 404
        self.m_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack('LL', 20, 0))
        
        data = [ ("uml", socket.gethostname()), ("port", self.m_socket.getsockname()[1]), ("short_name", short_name) ]
        self.m_socket.send ('GET /?%s HTTP/1.1\n\n' % urllib.urlencode(data))
        
        res = self.receiveoneline()  # comes back with True, "Ok"
        assert res.get("status") == "good", res


    def request(self, req):
        assert type(req) == dict, req
        assert "maincommand" in req
        self.m_socket.sendall(json.dumps(req) + '\n')
        return self.receiveoneline()

    def close(self) :
        if self.m_socket:
            try:
                # Try and flush some data but bear in mind that the proxy may have already 
                # closed the connection for us - as it does tend to do from time to time
                #self.m_socket.send('.\n')
                self.m_socket.close()
            except:
                pass
                
        self.m_socket = None

    # a \n delimits the end of the record.  you cannot read beyond it or it will hang; unless there is a moredata=True parameter
    def receiveonelinenj(self):
        
        while len(self.sbuffer) >= 2:
            res = self.sbuffer.pop(0)
            if res:
                return res
                
        while True:
            srec = self.m_socket.recv(1024)
            if not srec:
                return json.dumps({'error': "socket from dataproxy has unfortunately closed"})
            ssrec = srec.split("\n")  # multiple strings if a "\n" exists
            self.sbuffer.append(ssrec.pop(0))
            if ssrec:
                break # Discard anything after the newline
        
        line = "".join(self.sbuffer)
        self.sbuffer = ssrec
        return line
        
        
    def receiveoneline(self):
        self.sbuffer = [ ] # reset the buffer just for sake of that's what's worked in the past
        try:
            ret = json.loads(self.receiveonelinenj())
        except ValueError, e:
            raise Exception( e.message )
        assert "moredata" not in ret
        return ret
    