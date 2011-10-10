# -*- coding: utf-8 -*-

import string
import socket
import urllib
import urllib2
import cgi
import datetime
import types
import socket
import re
import os
import scraperwiki

try   : import json
except: import simplejson as json

import scraperwiki

m_socket = None
m_host = None
m_port = None
m_scrapername = None
m_runid = None
m_webstore_port = None   # if not null then will connect to new webstore
m_attachables = [ ]

        # make everything global to the module for simplicity as opposed to half in and half out of a single class
def create(host, port, scrapername, runid, attachables, webstore_port):
    global m_host
    global m_port
    global m_scrapername
    global m_runid
    global m_attachables
    global m_webstore_port
    m_host = host
    m_port = int(port)
    m_scrapername = scrapername
    m_runid = runid
    m_attachables = m_attachables
    m_webstore_port = int(webstore_port)

        # a \n delimits the end of the record.  you cannot read beyond it or it will hang
def receiveoneline(socket):
    sbuffer = [ ]
    while True:
        srec = socket.recv(1024)
        if not srec:
            scraperwiki.dumpMessage({'message_type': 'chat', 'message':"socket from dataproxy has unfortunately closed"})
            break
        ssrec = srec.split("\n")  # multiple strings if a "\n" exists
        sbuffer.append(ssrec.pop(0))
        if ssrec:
            break
    line = "".join(sbuffer)
    return line


def ensure_connected():
    global m_socket
    global m_scrapername
    global m_runid
    
    if not m_socket:
        m_socket = socket.socket()
        m_socket.connect((m_host, m_port))

        # needed to make it work locally.  how has this ever worked?
        #data["uml"] = "uml001"
        data = {"uml": 'lxc', "port":m_socket.getsockname()[1]}

        data["vscrapername"] = m_scrapername
        data["vrunid"] = m_runid
        data["attachables"] = " ".join(m_attachables)
        m_socket.sendall('GET /?%s HTTP/1.1\n\n' % urllib.urlencode(data))
        line = receiveoneline(m_socket)  # comes back with True, "Ok"
        res = json.loads(line)
        assert res.get("status") == "good", res
        

def request(req):
    if m_webstore_port:
        return webstorerequest(req)
    
    ensure_connected()
    m_socket.sendall(json.dumps(req)+'\n')
    line = receiveoneline(m_socket)
    if not line:
        return {"error":"blank returned from dataproxy"}
    return json.loads(line)


def close():
    m_socket.sendall('.\n')  # what's this for?
    m_socket.close()
    m_socket = None



# old apiwrapper functions, used in the general emailer (though maybe should be inlined to that file)
apiurl = "http://api.scraperwiki.com/api/1.0/"

def getInfo(name, version=None, history_start_date=None, quietfields=None):
    query = {"name":name}
    if version:
        query["version"] = version
    if history_start_date:
        query["history_start_date"] = history_start_date
    if quietfields:
        query["quietfields"] = quietfields
    url = "%sscraper/getinfo?%s" % (apiurl, urllib.urlencode(query))
    ljson = urllib.urlopen(url).read()
    return json.loads(ljson)

def getRunInfo(name, runid=None):
    query = {"name":name}
    if runid:
        query["runid"] = runid
    url = "%sscraper/getruninfo?%s" % (apiurl, urllib.urlencode(query))
    ljson = urllib.urlopen(url).read()
    return json.loads(ljson)

def getUserInfo(username):
    query = {"username":username}
    url = "%sscraper/getuserinfo?%s" % (apiurl, urllib.urlencode(query))
    ljson = urllib.urlopen(url).read()
    return json.loads(ljson)


# put this nasty one back in
datastoresave = [ ]
def save(unique_keys, data, date=None, latlng=None, silent=False, table_name="swdata", verbose=2) :
    if not datastoresave:
        print "*** instead of scraperwiki.datastore.save() please use scraperwiki.sqlite.save()"
        datastoresave.append(True)
    if latlng:
        raise Exception("scraperwiki.datastore.save(latlng) has definitely been deprecated.  Put the values into the data")
    if date:
        data["date"] = date
    return scraperwiki.sqlite.save(unique_keys=unique_keys, data=data, table_name=table_name, verbose=verbose)
    

def getKeys(name):
    raise scraperwiki.sqlite.SqliteError("getKeys has been deprecated")

def getData(name, limit=-1, offset=0):
    raise scraperwiki.sqlite.SqliteError("getData has been deprecated")

def getDataByDate(name, start_date, end_date, limit=-1, offset=0):
    raise scraperwiki.sqlite.SqliteError("getDataByDate has been deprecated")

def getDataByLocation(name, lat, lng, limit=-1, offset=0):
    raise scraperwiki.sqlite.SqliteError("getDataByLocation has been deprecated")
    
def search(name, filterdict, limit=-1, offset=0):
    raise scraperwiki.sqlite.SqliteError("apiwrapper.search has been deprecated")

def webstorerequest(req):
    if req.get("maincommand") == "sqlitecommand":
        if req.get("command") == "attach":
            return "{'status': 'ok'}"    # done at the higher level
        elif req.get("command") == "commit":
            return "{'status': 'ok'}"    # no operation
        else:
            return {"error":'Unknown sqlitecommand: %s' % req.get("command")}
        return {"error":'Unknown maincommand: %s' % req.get("maincommand")}

    webstoreurl = "http://%s:%s" % (m_host, m_webstore_port)
    username = "resourcedir"  # gets it into the right subdirectory automatically!!!
    dirscrapername = m_scrapername
    if not m_scrapername:
        dirscrapername = "DRAFT__%s" % re.sub("[\.\-]", "_", m_runid)
    databaseurl = "%s/%s/%s" % (webstoreurl, username, dirscrapername)
    
    if req.get("maincommand") == "save_sqlite":
        table_name = req.get("swdatatblname")
        tableurl = "%s/%s" % (databaseurl, table_name)
        ldata = req.get("data")
        if type(ldata) == dict:
            ldata = [ldata]
        qsl = [ ("unique", key)  for key in req.get("unique_keys") ]
        
            # quick and dirty provision of column types to the webstore
        if ldata:
            jargtypes = { }
            for k, v in ldata[0].items():
                if v != None:
                        # serious issue encountered here as blob doesn't mean same thing in SqlAlchemy as it does in Sqlite
                        # in the former it's a binary string, in Sqlite it means an uncoerced column with no type affinity
                        # (and therefore ideal for saving of variables of different types)
                    #if k[-5:] == "_blob":
                    #    vt = "blob"  # coerced into affinity none
                    if type(v) == int:
                        vt = "integer"
                    elif type(v) == float:
                        vt = "real"
                    else:
                        vt = "text"
                    jargtypes[k] = vt
            qsl.append(("jargtypes", json.dumps(jargtypes)))

        target = "%s?%s" % (tableurl, urllib.urlencode(qsl))
        request = urllib2.Request(target)
        
        request.add_header("Accept", "application/json")
        request.add_data(json.dumps(ldata))
            
        
    elif req.get("maincommand") == "sqliteexecute":
        class PutRequest(urllib2.Request):
            def get_method(self):
                return "PUT"
        request = PutRequest(databaseurl)
        request.add_header("Accept", "application/json+tuples")

        record = {"query":req.get("sqlquery"), "params":req.get("data"), "attach":[]}
        for name, asattach in req.get("attachlist"):
            record["attach"].append({"user":username, "database":name, "alias":asattach, "securityhash":"somthing"})
            
        request.add_data(json.dumps(record))


    request.add_header("Content-Type", "application/json")
    request.add_header("X-Scrapername", m_scrapername)
    request.add_header("X-Runid", m_runid)
    try:
        url = urllib2.urlopen(request)
        result = url.read()
        url.close()
    except urllib2.HTTPError, e:
        result = e.read()  # the error
    jres = json.loads(result)
    
    # decode error messages that may be inconveniently packed somewhere into the structure (what a lot of hassle!)
    if jres.get("state") == "error":
        return { "error":jres.get("message", "error") }
    if (type(jres) == dict) and (type(jres.get("keys")) == list) and (type(jres.get("data")) == list):
        if "state" in jres["keys"] and len(jres["data"]) == 1:
            ddata = dict(zip(jres["keys"], jres["data"][0]))
            if ddata.get("state") == "error":
                return { "error":ddata.get("message", "error") }
    return jres
    
