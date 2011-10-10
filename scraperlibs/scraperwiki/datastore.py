# -*- coding: utf-8 -*-

import string
import socket
import urllib
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

# list of scrapers we have an automatic right to attach to (to demonstrate the interface)
# may come in through the ident call or as some hashencoding
# if it is not declared in this list, then a call to django to interrogate the access permissions between 
# this scraper and/or user (esp in case of draft scrapers) and the attaching scraper
attachables = [ "Douter_space_objects_parsecollector" ]

        # make everything global to the module for simplicity as opposed to half in and half out of a single class
def create(host, port, scrapername, runid):
    global m_host
    global m_port
    global m_scrapername
    global m_runid
    m_host = host
    m_port = int(port)
    m_scrapername = scrapername
    m_runid = runid

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
        data = {"uml":socket.gethostname(), "port":m_socket.getsockname()[1]}
        data["vscrapername"] = m_scrapername
        data["vrunid"] = m_runid
        data["attachables"] = " ".join(attachables)
        m_socket.sendall('GET /?%s HTTP/1.1\n\n' % urllib.urlencode(data))
        line = receiveoneline(m_socket)  # comes back with True, "Ok"
        res = json.loads(line)
        assert res.get("status") == "good", res
        

def request(req):
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

