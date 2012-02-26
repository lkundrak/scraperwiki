#!/usr/bin/env python
# ScraperWiki Limited
# David Jones, 2011-11-28

"""
Tests for the dataproxy/datastore/whatever that can test the common edge cases
and should exercise the python library at the same time.

Can be run with unittest, or specloud which is simpler because the test
names don't necessarily contain the word "test".
"""

import json
import os
import sys
import uuid
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.abspath(__file__),
                                '../../../scraperlibs/python/')))
import scraperwiki


class DataStoreTester(unittest.TestCase):
    """Create a datastore connection for the tests to use.
    """
    def setUp(self):
        scraperwiki.logfd = sys.stdout
        self.settings = our_settings()
        self.settings['scrapername'], self.settings['runid'] = self.random_details()
        update_settings_for_name(self.settings,self.settings['scrapername'])
        scraperwiki.datastore.create( **self.settings )
        
    def random_details(self):
        return 'x_' + str(uuid.uuid4()), str(uuid.uuid4()), 
        
    def tearDown(self):
        scraperwiki.datastore.close()
        
        
# All test classes should extend DataStoreTester
# so that setUp and tearDown happen correctly.
        
class BasicDataProxyTests( DataStoreTester ):
    """
    Basic tests that the data proxy is working and allowing us to query data
    """
    
    def should_select_row_when_saved(self):
        scraperwiki.sqlite.save(['id'], {'id':1})
        x = scraperwiki.sqlite.execute('select count(*) from swdata')
        self.assertEqual( x['data'][0][0], 1)
        
    def should_save_row_in_custom_table(self):
        scraperwiki.sqlite.save(['id'], {'id':1}, table_name='test table')
        x = scraperwiki.sqlite.execute('select count(*) from `test table`')
        self.assertEqual( x['data'][0][0], 1)        

    def should_not_save_row_in_swdata(self):
        def try_select():
            scraperwiki.sqlite.execute('select count(*) from `swdata`')
        scraperwiki.sqlite.save(['id'], {'id':1}, table_name='test table')
        self.assertRaises(Exception, try_select, [])


    def ensure_unauthorised_attach_is_denied(self):
        
        def try_attach():
            scraperwiki.sqlite.attach(attach_to,attach_to)         
            scraperwiki.sqlite.select('* from `%s`.test' % attach_to)

        settings = our_settings()
        settings['scrapername'], settings['runid'] = self.random_details()
        update_settings_for_name(settings,settings['scrapername'])        
        attach_to = settings['scrapername']
        scraperwiki.datastore.create( **settings )
        print scraperwiki.sqlite.save(['id'], {'id':1}, table_name='test')
        scraperwiki.datastore.close()

        settings = our_settings()
        # Deliberately using random credentials so that the datastore
        # will reject our connection.
        settings['scrapername'], settings['runid'] = self.random_details()
        update_settings_for_name(settings,settings['scrapername'])       
        scraperwiki.datastore.create( **settings )
        scraperwiki.sqlite.save(['id'], {'id':1}, table_name='test')
        # It turns out the datastore raises AssertionError; probably not
        # the best Exception to raise, but we're not fixing that in this
        # test.
        self.assertRaises(Exception, try_attach, [])
        print "attach_to", repr(attach_to)

    def should_download_sqlite_file(self):
        import base64
        
        scraperwiki.sqlite.save(['id'], {'id':1}, table_name='test table')
        initsqlitedata = scraperwiki.datastore.request({"maincommand":"sqlitecommand", "command":"downloadsqlitefile", "seek":0, "length":0})
        if "filesize" not in initsqlitedata:
            print str(initsqlitedata)
            return
        filesize = initsqlitedata['filesize']         
        size = 0
        memblock=100000
        for offset in range(0, filesize, memblock):
            sqlitedata = scraperwiki.datastore.request({"maincommand":"sqlitecommand", "command":"downloadsqlitefile", "seek":offset, "length":memblock})
            content = sqlitedata.get("content")
            if sqlitedata.get("encoding") == "base64":
                content = base64.decodestring(content)            
            print len(content), sqlitedata.get("length")
            self.failUnless( len(content) == sqlitedata.get("length") )
        
# Helper functions.

def update_settings_for_name(settings,name):
    import hashlib
    secret_key = '%s%s' % (name, settings['secret'],)
    settings['verification_key'] = hashlib.sha256(secret_key).hexdigest()  
    del settings['secret']

def our_settings():
    """Return a JSON object (that is, a dict) of the settings used for
    the test.  These are stored in the file "dev_test_settings.json".
    """

    return json.load(
      open(os.path.join(os.path.dirname(__file__),
                        "dev_test_settings.json")))
