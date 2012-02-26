from twisted.python import log

import ConfigParser
import hashlib
import types
import os, string, re, sys
import time, datetime
import sqlite3
import base64
import shutil
import logging
import urllib
import traceback
import json
import csv
import StringIO

from twisted.internet import reactor

logger = None  # filled in by dataproxy
ninstructions_progresshandler = 10000000  # about 0.4secs on Julian's laptop
resourcedir = None # filled in by dataproxy
attachauthurl = None # filled in by dataproxy

def authorizer_readonly(action_code, tname, cname, sql_location, trigger):
    #logger.debug("authorizer_readonly: %s, %s, %s, %s, %s" % (action_code, tname, cname, sql_location, trigger))

    readonlyops = [ sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_DETACH, 31 ]  # 31=SQLITE_FUNCTION missing from library.  codes: http://www.sqlite.org/c3ref/c_alter_table.html
    if action_code in readonlyops:
        return sqlite3.SQLITE_OK

    if action_code == sqlite3.SQLITE_PRAGMA:
        if tname in ["table_info", "index_list", "index_info", "page_size"]:
            return sqlite3.SQLITE_OK

    # SQLite FTS (full text search) requires this permission even when reading, and
    # this doesn't let ordinary queries alter sqlite_master because of PRAGMA writable_schema
    if action_code == sqlite3.SQLITE_UPDATE and tname == "sqlite_master":
        return sqlite3.SQLITE_OK

    return sqlite3.SQLITE_DENY

def authorizer_attaching(action_code, tname, cname, sql_location, trigger):
    #print "authorizer_attaching", (action_code, tname, cname, sql_location, trigger)
    if action_code == sqlite3.SQLITE_ATTACH:
        return sqlite3.SQLITE_OK
    return authorizer_readonly(action_code, tname, cname, sql_location, trigger)

def authorizer_writemain(action_code, tname, cname, sql_location, trigger):
    #logger.debug("authorizer_writemain: %s, %s, %s, %s, %s" % (action_code, tname, cname, sql_location, trigger))
    if sql_location == None or sql_location == 'main':  
        return sqlite3.SQLITE_OK
    return authorizer_readonly(action_code, tname, cname, sql_location, trigger)
    

#http://twistedmatrix.com/documents/current/core/howto/producers.html
class SQLiteDatabase(object):

    def __init__(self, short_name, short_name_dbreadonly, attachlist):
        self.Dclientnumber = -1

        self.short_name = short_name
        self.short_name_dbreadonly = short_name_dbreadonly
        self.attachlist = attachlist   # to be used to drive the attaches on setup

        self.attached = { } # name => [ asname1, ... ] list
        self.m_sqlitedbconn = None
        self.m_sqlitedbcursor = None
        self.authorizer_func = None  
        self.sqlitesaveinfo = { }  # tablename -> info

        if self.short_name:
            self.scraperresourcedir = os.path.join(resourcedir, self.short_name)

        self.cstate = ''
        self.etimestate = time.time()
        self.progressticks = 0
        self.totalprogressticks = 0
        
        self.timeout_tickslimit = 300    # about 2 minutes
        self.timeout_secondslimit = 180  # real time
        self.clientforresponse = None

    def close(self):
        logger.debug("client#%d calling close on database" % self.Dclientnumber)
        try:
            if self.m_sqlitedbcursor:
                self.m_sqlitedbcursor.close()
            if self.m_sqlitedbconn:
                self.m_sqlitedbconn.close()
        except Exception, e:
            logger.warning("client#%d close database error: %s" % (self.Dclientnumber, str(e)))
            
            
            
    def process(self, request):
        #logger.debug("doing request %s" % str(request)[:1000])
        if request["maincommand"] == 'save_sqlite':
            res = self.save_sqlite(unique_keys=request["unique_keys"], data=request["data"], swdatatblname=request["swdatatblname"])
            logger.debug("save_sqlite response %s" % str(res))
        elif request["maincommand"] == 'clear_datastore':
            res = self.clear_datastore()
        elif request["maincommand"] == 'undelete_datastore':
            res = self.undelete_datastore()
        elif request["maincommand"] == 'sqlitecommand':
            if request["command"] == "downloadsqlitefile":
                res = self.downloadsqlitefile(seek=request["seek"], length=request["length"])
            elif request["command"] == "datasummary":
                res = self.datasummary(request.get("limit", 10))
            else:
                res = {"error":'Unknown command: %s' % request["command"]}
                
        elif request["maincommand"] == "sqliteexecute":
            if self.attachlist:
                self.establishconnection(True)
                for req in self.attachlist:
                    if req["asname"] not in self.attached.get(req["name"], []):
                        ares = self.sqliteattach(req["name"], req["asname"])
                        if "error" in ares:
                            return ares
            self.cstate, self.etimestate = 'sqliteexecute', time.time()
            res = self.sqliteexecute(sqlquery=request["sqlquery"], data=request["data"])
            if 'error' not in res:
                res["stillproducing"] = "yes"
            
        else:
            res = {"error":'Unknown maincommand: %s' % request["maincommand"]}
            logger.debug(json.dumps(res))

        return res


    def undelete_datastore(self):
        restore_from = os.path.join(self.scraperresourcedir, "DELETED-defaultdb.sqlite")
        if os.path.isfile(restore_from):
            restore_to = os.path.join(self.scraperresourcedir, "defaultdb.sqlite")
            shutil.move(restore_from, restore_to)
        return {"status":"good"}
        

    def clear_datastore(self):
        scrapersqlitefile = os.path.join(self.scraperresourcedir, "defaultdb.sqlite")
        if os.path.isfile(scrapersqlitefile):
            deletedscrapersqlitefile = os.path.join(self.scraperresourcedir, "DELETED-defaultdb.sqlite")
            shutil.move(scrapersqlitefile, deletedscrapersqlitefile)
        return {"status":"good"}

    
            # To do this properly would need to ensure file doesn't change during this process
    def downloadsqlitefile(self, seek, length):
        self.cstate, self.etimestate = 'downloadsqlitefile', time.time()

        scrapersqlitefile = os.path.join(self.scraperresourcedir, "defaultdb.sqlite")
        lscrapersqlitefile = os.path.join(self.short_name, "defaultdb.sqlite")
        if not os.path.isfile(scrapersqlitefile):
            return {"status":"No sqlite database"}
        
        result = { "filename":lscrapersqlitefile, "filesize": os.path.getsize(scrapersqlitefile)}
        if length == 0:
            return result
        
        fin = open(scrapersqlitefile, "rb")
        fin.seek(seek)
        content = fin.read(length)
        result["length"] = len(content)
        result["content"] = base64.encodestring(content)
        result['encoding'] = "base64"
        fin.close()
        
        return result
    
    
    def establishconnection(self, bcreate):
        
            # seems not able to reset authorizer function after it has been set once, so have to redirect this way
        def authorizer_all(action_code, tname, cname, sql_location, trigger):
            #print "authorizer_all", (action_code, tname, cname, sql_location, trigger)
            return self.authorizer_func(action_code, tname, cname, sql_location, trigger)
        
        if self.short_name_dbreadonly:
            self.authorizer_func = authorizer_readonly
        else:
            self.authorizer_func = authorizer_writemain
        
        if not self.m_sqlitedbconn:
            if self.short_name:
                if not os.path.isdir(self.scraperresourcedir):
                    if not bcreate: 
                        return False
                    os.mkdir(self.scraperresourcedir)
                scrapersqlitefile = os.path.join(self.scraperresourcedir, "defaultdb.sqlite")
                self.m_sqlitedbconn = sqlite3.connect(scrapersqlitefile, check_same_thread=False)
                logger.debug('Connecting to %s' % (scrapersqlitefile))
            else:
                self.m_sqlitedbconn = sqlite3.connect(":memory:", check_same_thread=False)   # draft scrapers make a local version
            if not self.short_name_dbreadonly:
                self.m_sqlitedbconn.isolation_level = None   # autocommit!
                
            self.m_sqlitedbconn.set_authorizer(authorizer_all)
            if ninstructions_progresshandler:
                self.m_sqlitedbconn.set_progress_handler(self.progress_handler, ninstructions_progresshandler)   
            self.m_sqlitedbcursor = self.m_sqlitedbconn.cursor()
             
        return True
                
                
    def datasummary(self, limit):
        self.cstate, self.etimestate = 'datasummary', time.time()
        if not self.establishconnection(False):
            logger.warning( 'Failed to connect to sqlite database for summary %s' % (self.short_name or 'draft'))
            return {"status":"No sqlite database"} # don't change this return string, is a structured one

        logger.debug('Performing datasummary for %s' % self.short_name)                
                        
        self.authorizer_func = authorizer_readonly
        total_rows = 0
        tables = { }
        try:
            for name, sql in list(self.m_sqlitedbcursor.execute("select name, sql from sqlite_master where type='table' or type='view'")):
                tables[name] = {"sql":sql}

                cols = []
                self.m_sqlitedbcursor.execute("PRAGMA table_info(`%s`);" % name)

                # We can optimise the count by doing all tables in sub-selects, but suspect it is a micro-optimisation
                tables[name]["keys"] = [ r[1] for r in self.m_sqlitedbcursor]
                tables[name]["count"] = list(self.m_sqlitedbcursor.execute("select count(1) from `%s`" % name))[0][0]
                total_rows += int(tables[name]["count"])
                
        except sqlite3.Error, e:
            return {"error":"datasummary: sqlite3.Error: "+str(e)}
        
        result = {"tables":tables, 'total_rows': total_rows }
        if self.short_name:
            scrapersqlitefile = os.path.join(self.scraperresourcedir, "defaultdb.sqlite")
            if os.path.isfile(scrapersqlitefile):
                result["filesize"] = os.path.getsize(scrapersqlitefile)
                 
        return result


    def sqliteattach(self, name, asname):
        logger.debug("attach to %s  %s as %s" % (self.short_name, name, asname))
        self.establishconnection(True)
        if self.authorizer_func == authorizer_writemain:
            self.m_sqlitedbconn.commit()  # otherwise a commit will be invoked by the attaching function
        
        logger.info("requesting permission to attach %s to %s" % (self.short_name, name))
        
        aquery = {"command":"can_attach", "scrapername":self.short_name, "attachtoname":name, "username":"unknown"}
        ares = urllib.urlopen("%s?%s" % (attachauthurl, urllib.urlencode(aquery))).read()
        logger.info("permission to attach %s to %s response: %s" % (self.short_name, name, ares))
        
        if ares == "Yes":
            logger.debug('attach connection allowed')
        elif ares == "DoesNotExist":
            return {"error":"Does Not Exist %s" % name}
        else:
            return {"error":"no permission to attach to %s" % name}

        attachscrapersqlitefile = os.path.join(resourcedir, name, "defaultdb.sqlite")
        self.authorizer_func = authorizer_attaching
        try:
            self.m_sqlitedbcursor.execute('attach database ? as ?', (attachscrapersqlitefile, asname or name))
        except sqlite3.Error, e:
            logger.error(e)
            return {"error":"sqliteattach: sqlite3.Error: "+str(e)}
        logger.debug('attach complete')
        
        if name not in self.attached:
             self.attached[name] = [ ]
        self.attached[name].append(asname)
        return {"status":"attach succeeded"}


    def progress_handler(self):
        if self.cstate == 'sqliteexecute':
             self.progressticks += 1
             self.totalprogressticks += 1
             if self.progressticks == self.timeout_tickslimit:
                 logger.info("client#%d tickslimit timeout" % (self.Dclientnumber))
                 return 1
             if time.time() - self.etimestate > self.timeout_secondslimit:
                 logger.info("client#%d elapsed time timeout" % (self.Dclientnumber))
                 return 2
        logger.debug("client#%d progress %d time=%.2f" % (self.Dclientnumber, self.progressticks, time.time() - self.etimestate))
        
            # looks like should be using IBodyPushProducer for this cycle
            # but prob couldn't work as we are in a deferred thread here
        lclientforresponse = self.clientforresponse
        if not lclientforresponse:
            logger.info("client#%d terminating progress" % (self.Dclientnumber))  # as nothing to receive the result anyway
            return 3
        elif lclientforresponse.progress_ticks == "yes":
            jtickline = json.dumps({"progresstick":self.progressticks, "timeseconds":time.time() - self.etimestate})+"\n"
                # should this be using IPushProducer?
            reactor.callFromThread(lclientforresponse.transport.write, jtickline)

        return 0  # continue
        
        
    def sqliteexecute(self, sqlquery, data):
        self.establishconnection(True)
        self.progressticks = 0
        try:
            logger.info("client#%d sqlexecute %s" % (self.Dclientnumber, str(sqlquery)[:100]))  
            if data:
                self.m_sqlitedbcursor.execute(sqlquery, data)  # handle "(?,?,?)", (val, val, val)
            else:
                self.m_sqlitedbcursor.execute(sqlquery)
            logger.info("client#%d end-sqlexecute %f" % (self.Dclientnumber, time.time() - self.etimestate))  

                # take a copy of the clientforresponse as it may be disconnected by the other thread
            lclientforresponse = self.clientforresponse
            if not lclientforresponse:
                return {"error":"client must have disconnected"}

            keys = self.m_sqlitedbcursor.description and map(lambda x:x[0], self.m_sqlitedbcursor.description) or []
            arg = {"keys":keys, "data":[] }   # data empty for filling in in another function

        except sqlite3.Error, e:
            arg = {"error":"sqliteexecute: sqlite3.Error: %s" % str(e)}
        except ValueError, ve:
            arg = {"error":"sqliteexecute: ValueError: %s" % str(ve)}
        if "error" in arg:
            logger.error(arg["error"])
        arg["progressticks"] = self.progressticks
        arg["timeseconds"] = time.time() - self.etimestate
        return arg


    def save_sqlite(self, unique_keys, data, swdatatblname):
        self.cstate, self.etimestate = 'save_sqlite', time.time()
        res = { }
        if type(data) == dict:
            data = [data]
        
        if not self.m_sqlitedbconn or swdatatblname not in self.sqlitesaveinfo:
            ssinfo = SqliteSaveInfo(self, swdatatblname)
            self.sqlitesaveinfo[swdatatblname] = ssinfo
            if not ssinfo.rebuildinfo() and data:
                ssinfo.buildinitialtable(data[0])
                ssinfo.rebuildinfo()
                res["tablecreated"] = swdatatblname
        else:
            ssinfo = self.sqlitesaveinfo[swdatatblname]
        
        nrecords = 0
        self.sqliteexecute("BEGIN TRANSACTION", None)
        logger.debug("client#%d begintrans for records %d" % (self.Dclientnumber, len(data)))
        for ldata in data:
            newcols = ssinfo.newcolumns(ldata)
            if newcols:
                for i, kv in enumerate(newcols):
                    ssinfo.addnewcolumn(kv[0], kv[1])
                    res["newcolumn %d" % i] = "%s %s" % kv
                ssinfo.rebuildinfo()

            if nrecords == 0 and unique_keys:
                idxname, idxkeys = ssinfo.findclosestindex(unique_keys)
                if not idxname or idxkeys != set(unique_keys):
                    lres = ssinfo.makenewindex(idxname, unique_keys)
                    if "error" in lres:  
                        return lres
                    res.update(lres)
            
            values = [ ldata.get(k)  for k in ssinfo.swdatakeys ]
            lres = self.sqliteexecute(ssinfo.sqdatatemplate, values)
            if "error" in lres:  
                return lres
            nrecords += 1
        logger.debug("client#%d about to endtrans" % (self.Dclientnumber))
        self.sqliteexecute("END TRANSACTION", None)
        logger.debug("client#%d endtrans" % (self.Dclientnumber))
        #self.m_sqlitedbconn.commit()
        
        res["nrecords"] = nrecords
        res["status"] = 'Data record(s) inserted or replaced'
        self.cstate = ''
        return res


    def FetchRows(self, nrows=-1):
        rows = []
        for r in self.m_sqlitedbcursor:
            row = []
            for c in r:
                if type(c) == buffer:
                    row.append( unicode(c) )
                else:
                    row.append(c)
            rows.append(row)
            if nrows != -1 and len(rows) == nrows:
                break
        return rows



class SqliteSaveInfo:
    def __init__(self, database, swdatatblname):
        self.database = database
        self.swdatatblname = swdatatblname
        self.swdatakeys = [ ]
        self.swdatatypes = [  ]
        self.sqdatatemplate = ""

    def sqliteexecuteSS(self, sqlquery, data=None):
        res = self.database.sqliteexecute(sqlquery, data)
        if "error" in res:
            logger.warning("%s  %s" % (self.database.short_name, str(res)[:1000]))
        res["data"] = self.database.FetchRows()
        return res
    
    def rebuildinfo(self):
        if not self.sqliteexecuteSS("select * from main.sqlite_master where name=?", (self.swdatatblname,))['data']:
            return False

        tblinfo = self.sqliteexecuteSS("PRAGMA main.table_info(`%s`)" % self.swdatatblname)
            # there's a bug:  PRAGMA main.table_info(swdata) returns the schema for otherdatabase.swdata 
            # following an attach otherdatabase where otherdatabase has a swdata and main does not
        
        self.swdatakeys = [ a[1]  for a in tblinfo["data"] ]
        self.swdatatypes = [ a[2]  for a in tblinfo["data"] ]
        self.sqdatatemplate = "insert or replace into main.`%s` values (%s)" % (self.swdatatblname, ",".join(["?"]*len(self.swdatakeys)))
        return True
    
            
    def buildinitialtable(self, data):
        assert not self.swdatakeys
        coldef = self.newcolumns(data)
        assert coldef
        # coldef = coldef[:1]  # just put one column in; the rest could be altered -- to prove it's good
        scoldef = ", ".join(["`%s` %s" % col  for col in coldef])
                # used to just add date_scraped in, but without it can't create an empty table
        self.sqliteexecuteSS("create table main.`%s` (%s)" % (self.swdatatblname, scoldef))
    
    def newcolumns(self, data):
        newcols = [ ]
        for k in data:
            if k not in self.swdatakeys:
                v = data[k]
                if v != None:
                    if k[-5:] == "_blob":
                        vt = "blob"  # coerced into affinity none
                    elif type(v) == int:
                        vt = "integer"
                    elif type(v) == float:
                        vt = "real"
                    else:
                        vt = "text"
                    newcols.append((k, vt))
        return newcols

    def addnewcolumn(self, k, vt):
        self.sqliteexecuteSS("alter table main.`%s` add column `%s` %s" % (self.swdatatblname, k, vt))

    def findclosestindex(self, unique_keys):
        idxlist = self.sqliteexecuteSS("PRAGMA main.index_list(`%s`)" % self.swdatatblname)  # [seq,name,unique]
        uniqueindexes = [ ]
        if 'error' in idxlist:
            return None, None
            
        for idxel in idxlist["data"]:
            if idxel[2]:
                idxname = idxel[1]
                idxinfo = self.sqliteexecuteSS("PRAGMA main.index_info(`%s`)" % idxname) # [seqno,cid,name]
                idxset = set([ a[2]  for a in idxinfo["data"] ])
                idxoverlap = len(idxset.intersection(unique_keys))
                uniqueindexes.append((idxoverlap, idxname, idxset))
        
        if not uniqueindexes:
            return None, None
        uniqueindexes.sort()
        return uniqueindexes[-1][1], uniqueindexes[-1][2]

    # increment to next index number every time there is a change, and add the new index before dropping the old one.
    def makenewindex(self, idxname, unique_keys):
        istart = 0
        if idxname:
            mnum = re.search("(\d+)$", idxname)
            if mnum:
                istart = int(mnum.group(1))
        for i in range(10000):
            newidxname = "%s_index%d" % (self.swdatatblname, istart+i)
            if not self.sqliteexecuteSS("select name from main.sqlite_master where name=?", (newidxname,))['data']:
                break
            
        res = { "newindex": newidxname }
        lres = self.sqliteexecuteSS("create unique index `%s` on `%s` (%s)" % (newidxname, self.swdatatblname, ",".join(["`%s`"%k  for k in unique_keys])))
        if "error" in lres:  
            return lres
        if idxname:
            lres = self.sqliteexecuteSS("drop index main.`%s`" % idxname)
            if "error" in lres:  
                if lres["error"] != 'sqlite3.Error: index associated with UNIQUE or PRIMARY KEY constraint cannot be dropped':
                    return lres
                logger.info("%s:  %s" % (self.database.short_name, str(lres)[:1000]))
            res["droppedindex"] = idxname
        return res
            

