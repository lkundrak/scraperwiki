import unittest
import uuid, os, urllib, urllib2, re, datetime, time
import json, csv
from selenium import selenium
from selenium_test import SeleniumTest

class TestApi(SeleniumTest):
    
    populate_db_name = None
    
    user_name = None
    user_pass = None
    
    site_base = None
    api_base = None
    
    private_scraper_error = {
        "short_name": None, 
        "error": "Invalid API Key"
    }
    
    user_api_key = None
    scraper_api_key = None
    
    # TODO: use these for checking runevents until the codemirror 'run' button
    # is updated to generate runevents.
    hardcoded_runevent_scraper = "runevent_api_test"
    hardcoded_private_runevent_scraper = "private_runevent_api_test"
    
    # TODO list:
    # Check callbacks are generated properly (simple test)
    # Once the codemirror 'run' button can dynamically generate a runevent, 
    #    - Update _scraperinfo_date_test
    #    - Update _runinfo_test
    #    - Update _runinfo_privacy_test
    #    - Remove the hardcoded_* variables above
    # Add scraper title search test to test_search_apis
    # Update _datastore_privacy_test when table attach error message is corrected to 'permission denied' instead of 'not found'
    # Test DB attachments in _datastore_privacy_test when it's updated to not use the code permissions table
    # Make a test query that joins a DB in _advanced_datastore_query
    # Do the privacy tests for vaulted scrapers - should be the same as private

    def test_datastore_api(self):
        self._get_api_base()
        self._setup_db()
        self._basic_datastore_query()
        self._advanced_datastore_query()
        
    def test_scraperinfo_api(self):
        self._get_api_base()
        self._setup_db()
        self._scraperinfo_quietfields_test()
        self._scraperinfo_date_test() 
        self._scraperinfo_version_test()
        
    def test_runinfo_api(self):
        self._get_api_base()
        self._setup_db()
        self._runinfo_test()
        
    def test_userinfo_api(self):
        self._get_api_base()
        self._setup_db()
        self._userinfo_username_test()
        if SeleniumTest._adminuser['username'] and SeleniumTest._adminuser['password']:
            self._userinfo_roles_test()
        else:
            print "Roles in the userinfo api cannot be checked without an admin account"
        
    def test_search_apis(self):
        self._get_api_base()
        self._setup_db()
        self._scrapersearch_shortname_test()
        self._scrapersearch_description_test()
        self._usersearch_test()
        
    def test_api_privacy(self):
        if not (SeleniumTest._adminuser['username'] and SeleniumTest._adminuser['password']):
            print "Cannot perform privacy test without an admin account specified"
            return
        self._get_api_base()
        self._setup_db()
        self.user_api_key = self._set_api_key("user", self.user_name)
        self.scraper_api_key = self._set_api_key("scraper", self.populate_db_name)
        self.private_scraper_error["short_name"] = self.populate_db_name
        self.activate_users([self.user_name])
        self.set_code_privacy("private", "scraper", self.populate_db_name, 
                            {'username':self.user_name, 'password':self.user_pass})
        self._datastore_privacy_test()
        self._scraperinfo_privacy_test()
        self._runinfo_privacy_test()
        self._userinfo_privacy_test()
        self._scrapersearch_privacy_test()
        
        
        
        
        
    def _datastore_privacy_test(self):
        """ Check that private scrapers behave as expected """
        s = self.selenium
        # Prepare for attaching a scraper
        with open(os.path.join( os.path.dirname( __file__ ), 'sample_data/python_scraper.txt')) as file:
            public_scraper_code = file.read().replace('&','&amp').replace('<','&lt').replace('>','&gt').replace('\n', '<br>')
        public_scraper = self.create_code("python", "scraper", public_scraper_code)
        
        # Expect failures (even when logged in for api tests)
        # Check sqlite download, need to log out to ensure correct rejection
        s.open("/logout")
        self.wait_for_page()
        try:
            sqlite_file = urllib2.urlopen(self.site_base + "scrapers/export_sqlite/%s/" % self.populate_db_name)
            # Should have thrown a 403
            self.fail()
        except urllib2.HTTPError as exception:
            self.failUnless(exception.code == 403)
        self.user_login(self.user_name, self.user_pass)
        # Check sql query json
        response = urllib2.urlopen(self.api_base + "datastore/sqlite?" + 
                                    urllib.urlencode({"format":"jsondict","name":self.populate_db_name,"query":"select * from swdata"}))
        self.failUnless(json.loads(response.read()) == self.private_scraper_error)
        # Attach DB privacy
        response = urllib2.urlopen(self.api_base + "datastore/sqlite?format=jsondict&name=" + public_scraper + 
                                   "&attach=" + self.populate_db_name + "&query=select%20*%20from%20" + self.populate_db_name + ".swdata%20limit%2010")
        # TODO: waiting for this error message to be corrected
        self.failUnless(json.loads(response.read()) == {"error": "sqlite3.Error: no such table: " + self.populate_db_name + ".swdata"})
        
        # Now test for expected successes
        # Check SQLite downloading (based on logged in user)
        sqlite_file = urllib2.urlopen(urllib2.Request(self.site_base + "scrapers/export_sqlite/%s/" % self.populate_db_name, headers={'cookie':s.get_cookie()}))
        self.failUnless(int(sqlite_file.headers.dict['content-length']) > 0)
        self.failUnless(sqlite_file.headers.dict['content-type'] == 'application/octet-stream')
        self.failUnless(sqlite_file.headers.dict['content-disposition'] == 'attachment; filename=%s.sqlite' % self.populate_db_name)
        # Check CSV downloading (api key embedded in link for logged in user)
        s.open("/scrapers/" + self.populate_db_name)
        self.wait_for_page()
        csvurl = s.get_attribute("downloadcsvtable@href")
        response = urllib2.urlopen(csvurl)
        self.failUnless(response.headers.dict['content-disposition'] == "attachment; filename=" + self.populate_db_name + ".csv" )
        self.failUnless(len(response.read()) > 0)
        self.failUnless(response.headers.dict['content-type'] == 'text/csv')
        # SQL query JSON
        s.open("/logout")
        self.wait_for_page()
        response = urllib2.urlopen(self.api_base + "datastore/sqlite?format=jsondict&name=" + self.populate_db_name + 
                                    "&query=select%20*%20from%20swdata&apikey=" + self.scraper_api_key)
        self.failUnless(len(json.loads(response.read())) == 20)
        
    
    def _scraperinfo_privacy_test(self):
        """ Make sure scraperinfo of a private scraper fails unless correct api key specified """
        # Expecting failure
        url = self.api_base + "scraper/getinfo?format=jsondict&name=" + self.populate_db_name
        scraperinfo = json.loads(urllib2.urlopen(url).read())[0]
        self.failUnless(scraperinfo == self.private_scraper_error)
        
        # Use api key, expect success
        url = self.api_base + "scraper/getinfo?format=jsondict&name=" + self.populate_db_name + "&apikey=" + self.scraper_api_key
        scraperinfo = json.loads(urllib2.urlopen(url).read())[0]
        self.failUnless(scraperinfo['privacy_status'] == "private" and scraperinfo['code'])
    
    
    def _runinfo_privacy_test(self):
        """ Make sure runinfo of a private scraper fails """
        # The first runids and api keys of the private scrapers
        if "dev.scraperwiki.com" in self.site_base:
            runid = '1316771145.348448_e6b400b9-6a6e-446d-b04e-d9e3b6b667e1'
            api_key = "02d8ab83-bec0-4934-a1a0-cc75b4df09a4"
        elif "scraperwiki.com" in self.site_base:
            runid = '1316897325.456186_009f2d99-df7a-4d86-9115-6654c6812106'
            api_key = "d82c1c3a-f690-442c-8b75-6c5a09185647"
        else:
            # TODO: can't generate runevents dynamically (e.g. on localhost) yet
            return
        # Can't use the private scraper we've just set up because it will have no runevents
        runevent_error = self.private_scraper_error
        runevent_error["short_name"] = self.hardcoded_private_runevent_scraper
        
        # Get most recent runevent
        jsonresponse = json.loads(urllib2.urlopen(self.api_base + "scraper/getruninfo?" + "format=jsondict&name=" + 
                                  self.hardcoded_private_runevent_scraper).read())
        self.failUnless(jsonresponse == runevent_error)
        # Get first runevent
        jsonresponse = json.loads(urllib2.urlopen(self.api_base + "scraper/getruninfo?" + "format=jsondict&name=" + 
                                  self.hardcoded_private_runevent_scraper + "&runid=" + runid).read())
        self.failUnless(jsonresponse == runevent_error)
        
        # Try the above with the api key (defined in this function), expecting valid results now
        jsonresponse = json.loads(urllib2.urlopen(self.api_base + "scraper/getruninfo?" + "format=jsondict&name=" + 
                                  self.hardcoded_private_runevent_scraper + "&apikey=" + api_key).read())
        self.failUnless(len(jsonresponse) == 1)
        self.failUnless("output" in jsonresponse[0])
        self.failIf(jsonresponse[0]['runid'] == runid)
        jsonresponse = json.loads(urllib2.urlopen(self.api_base + "scraper/getruninfo?" + "format=jsondict&name=" + 
                                  self.hardcoded_private_runevent_scraper + "&runid=" + runid + "&apikey=" + api_key).read())
        self.failUnless(len(jsonresponse) == 1)
        self.failUnless("output" in jsonresponse[0])
        self.failUnless(jsonresponse[0]['runid'] == runid)
        
        
    def _userinfo_privacy_test(self):
        """ Check private scraper does not appear in the userinfo of the owner or an editor """
        # Create user and add as editor
        editorname = self.create_user()
        self.user_login(self.user_name, self.user_pass)
        self.selenium.open("/scrapers/" + self.populate_db_name)
        self.wait_for_page()
        self.add_code_editor(editorname, "test user (editor)") 
        
        # Check private scraper doesn't appear in either editor or owner info
        url = self.api_base + "scraper/getuserinfo?format=jsondict&username=" + self.user_name
        userinfo = json.loads(urllib2.urlopen(url).read())[0]
        self.failUnless(self.populate_db_name not in userinfo['coderoles']['owner'])
        url = self.api_base + "scraper/getuserinfo?format=jsondict&username=" + editorname
        userinfo = json.loads(urllib2.urlopen(url).read())[0]
        self.failUnless('editor' not in userinfo['coderoles'])
        
        # Now use an api key, expect the private scraper to appear
        url = self.api_base + "scraper/getuserinfo?format=jsondict&username=" + self.user_name + "&apikey=" + self.user_api_key
        userinfo = json.loads(urllib2.urlopen(url).read())[0]
        self.failUnless(self.populate_db_name in userinfo['coderoles']['owner'])
        url = self.api_base + "scraper/getuserinfo?format=jsondict&username=" + editorname + "&apikey=" + self.user_api_key
        userinfo = json.loads(urllib2.urlopen(url).read())[0]
        self.failUnless(self.populate_db_name in userinfo['coderoles']['editor'])
        
        
    def _scrapersearch_privacy_test(self):
        """ Check private scrapers are not returned """
        # Set description
        s = self.selenium
        description = str(uuid.uuid4())
        s.open(self.site_base + "scrapers/" + self.populate_db_name)
        self.wait_for_page()
        s.click('css=#aEditAboutScraper')
        s.type('css=#divAboutScraper textarea', description)
        s.click("//div[@id='divAboutScraper']//button[text()='Save']")
        time.sleep(1)
        
        # Do the private checking without an api key
        url = self.api_base + "scraper/search?format=jsondict&searchquery=" + self.populate_db_name
        results = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(results) == 0)
        url = self.api_base + "scraper/search?format=jsondict&searchquery=" + description
        results = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(results) == 0)
        
        # Now with an api key, expect results
        url = self.api_base + "scraper/search?format=jsondict&searchquery=" + self.populate_db_name + "&apikey=" + self.user_api_key
        results = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(results) == 1)
        url = self.api_base + "scraper/search?format=jsondict&searchquery=" + description + "&apikey=" + self.user_api_key
        results = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(results) == 1)
        
        
    def _usersearch_test(self):
        """ Make sure the user search returns a user based on username, profilename and with exclusions """
        s = self.selenium
        # Set the profile name
        profile_name = str( uuid.uuid4() )[:18].replace('-', '_')
        s.open("/profiles/edit/")
        self.wait_for_page()
        s.type('//input[@id="id_name"]', profile_name)
        s.click('//a[@class="submit_link _link"]')
        # Give a bit of time for the api to update
        s.open("/")
        self.wait_for_page()
        # Search by username
        url = self.api_base + "scraper/usersearch?format=jsondict&searchquery=" + self.user_name
        result = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(result) == 1)
        self.failUnless(result[0]['username'] == self.user_name)
        # Check for exclusions
        url = self.api_base + "scraper/usersearch?format=jsondict&searchquery=" + self.user_name + "&nolist=" + self.user_name
        result = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(result) == 0)
        # Search by profile name
        url = self.api_base + "scraper/usersearch?format=jsondict&searchquery=" + profile_name
        result = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(result) == 1)
        self.failUnless(result[0]['username'] == self.user_name)
        # Check for exclusions
        url = self.api_base + "scraper/usersearch?format=jsondict&searchquery=" + profile_name + "&nolist=" + self.user_name
        result = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(result) == 0)
        
        
    def _scrapersearch_description_test(self):
        """ Check description search works correctly """
        # Set description
        s = self.selenium
        description = str(uuid.uuid4())
        s.open(self.site_base + "scrapers/" + self.populate_db_name)
        self.wait_for_page()
        s.click('css=#aEditAboutScraper')
        s.type('css=#divAboutScraper textarea', description)
        s.click("//div[@id='divAboutScraper']//button[text()='Save']")
        time.sleep(1)
        # Search for description
        url = self.api_base + "scraper/search?format=jsondict&searchquery=" + description
        results = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(results) == 1)
        self.failUnless(results[0]['short_name'] == self.populate_db_name)
        self.failUnless(results[0]['privacy_status'] == "public")
        
        
    def _scrapersearch_shortname_test(self):
        """ Check shortname search works correctly, use the emailer as a readymade scraper """
        url = self.api_base + "scraper/search?format=jsondict&searchquery=" + self.user_name + ".emailer"
        results = json.loads(urllib2.urlopen(url).read())
        self.failUnless(len(results) == 1)
        self.failUnless(results[0]['short_name'] == self.user_name + ".emailer")
        self.failUnless(results[0]['privacy_status'] == "visible")
        
        
    def _userinfo_roles_test(self):
        """ Check scrapers correctly appear when a user is an owner, editor and follower """
        s = self.selenium
        # Check scrapers user is owner of
        params = {"format" : "jsondict", "username" : self.user_name}
        userinfo = json.loads(urllib2.urlopen(self.api_base + "scraper/getuserinfo?" + urllib.urlencode(params)).read())[0]
        self.failUnless(self.populate_db_name in userinfo['coderoles']['owner'])
        # Set privacy, create a new user and add them as an editor in preparation
        self.activate_users([self.user_name])
        editorname = self.create_user()
        self.user_login(self.user_name, self.user_pass)
        s.open("/scrapers/" + self.populate_db_name)
        self.wait_for_page()
        self.set_code_privacy("protected", "scraper")
        self.add_code_editor(editorname, "test user (editor)")
        # Check user is now an editor
        params = {"format" : "jsondict", "username" : editorname}
        userinfo = json.loads(urllib2.urlopen(self.api_base + "scraper/getuserinfo?" + urllib.urlencode(params)).read())[0]
        self.failUnless(self.populate_db_name in userinfo['coderoles']['editor'])
        
        
    def _userinfo_username_test(self):
        """ Check the api returns correct values for username and profile name"""
        params = {"format" : "jsondict", "username" : self.user_name}
        s = self.selenium
        # Set the profile name
        profile_name = str( uuid.uuid4() )[:18].replace('-', '_')
        s.open("/profiles/edit/")
        self.wait_for_page()
        s.type('//input[@id="id_name"]', profile_name)
        s.click('//a[@class="submit_link _link"]')
        self.wait_for_page()
        # Get the results
        userinfo = json.loads(urllib2.urlopen(self.api_base + "scraper/getuserinfo?" + urllib.urlencode(params)).read())[0]
        self.failUnless(userinfo['username'] == self.user_name)
        self.failUnless(userinfo['profilename'] == profile_name)
        
        
    def _runinfo_test(self):
        """ Check that querying for runevents works """
        # The first runids of the protected scrapers
        if "dev.scraperwiki.com" in self.site_base:
            runid = '1316774565.339344_f13fe242-6121-4a55-ad80-b21ac4bc8412'
        elif "scraperwiki.com" in self.site_base:
            runid = '1316646705.182498_7220cef2-a698-4205-ae14-aba4c85459d2'
        else:
            # TODO: can't generate runevents dynamically (e.g. on localhost) yet
            return
        # Get most recent runevent
        jsonresponse = json.loads(urllib2.urlopen(self.api_base + "scraper/getruninfo?" + 
                                  "format=jsondict&name=" + self.hardcoded_runevent_scraper).read())
        self.failUnless(len(jsonresponse) == 1)
        self.failUnless("output" in jsonresponse[0])
        self.failIf(jsonresponse[0]['runid'] == runid)
        # Get first runevent
        jsonresponse = json.loads(urllib2.urlopen(self.api_base + "scraper/getruninfo?" + 
                                  "format=jsondict&name=" + self.hardcoded_runevent_scraper + 
                                  "&runid=" + runid).read())
        self.failUnless(len(jsonresponse) == 1)
        self.failUnless("output" in jsonresponse[0])
        self.failUnless(jsonresponse[0]['runid'] == runid)
        
    
    def _scraperinfo_version_test(self):
        """ Make a small change in the code, save and check versions api works as expected """
        s = self.selenium
        populate_db_file = open(os.path.join( os.path.dirname( __file__ ), 'sample_data/populate_db_scraper.txt'))
        code = populate_db_file.read()
        html_code = code.replace('&','&amp').replace('<','&lt').replace('>','&gt').replace('\n', '<br>')
        populate_db_file.close()
        
        s.type_keys('//body[@class="editbox"]', "\16")
        s.wait_for_condition("selenium.browserbot.getCurrentWindow().document.getElementById('btnCommitPopup').disabled == false", 10000)
        s.type('//body[@class="editbox"]', "%s" % (html_code + '# A change'))
        s.click('btnCommitPopup')

        json = self._get_info(self.populate_db_name)
        self.failUnless(json[0]['code'] == code + '# A change')
        json = self._get_info(self.populate_db_name, version='-1')
        self.failUnless(json[0]['code'] == code + '# A change')
        json = self._get_info(self.populate_db_name, version='0')
        self.failUnless(json[0]['code'] == code)
        
        
    def _scraperinfo_date_test(self):
        """ Check that scraper info correctly filters run events """
        # TODO: waiting on the codemirror 'run' button to generate a run event
        # Currently uses a hardcoded scraper on dev and live
        if "localhost" in self.site_base:
            return
        # Arbitrary date in the future and arbitrary date in the past
        futuredate = str(datetime.date.fromtimestamp(time.time()+1000000).isoformat())
        pastdate =   str(datetime.date.fromtimestamp(time.time()-1000000).isoformat())
        scrapername = self.hardcoded_runevent_scraper
        # Check a future date filter returns no run events and that at least one is returned for a past date
        checks = [{'json':self._get_info(scrapername, history_start_date=futuredate), 'results':(lambda x:x==0) },
                  {'json':self._get_info(scrapername, history_start_date=pastdate),   'results':(lambda x:x>=1) }]
        for check in checks:
            json = check['json']
            self.failUnless( check['results'](len(json[0]['runevents'])) )


    def _scraperinfo_quietfields_test(self):
        """ Check scraper info response fields are as expected """
        always_fields = ['description','language','title','tags','short_name','created','records','filemodifieddate',
                         'wiki_type','privacy_status','attachable_here','attachables','modifiedcommitdifference']
        fields = ['code','runevents','datasummary','userroles','history','prevcommit']
        
        # Check trying to make all fields quiet leaves irremovable ones alone, and that all fields are present by default
        checks = [{'json':self._get_info(self.populate_db_name, quietfields='|'.join(always_fields+fields)), 'keys':always_fields[:]           },
                  {'json':self._get_info(self.populate_db_name),                                             'keys':always_fields[:]+fields[:] }]
        
        for check in checks:
            json = check['json']
            keys = check['keys']
            for key in json[0].keys():
                keys.remove(key)
            self.failUnless(keys == [])
            self.failUnless(json[0]['short_name'] ==self.populate_db_name)
        
        
    def _basic_datastore_query(self):
        """ Basic tests on parameters of datastore api queries
        Includes sqlite download and output formats """
        # Check download of sqlite file
        sqlite_file = urllib2.urlopen(self.site_base + "scrapers/export_sqlite/%s/" % self.populate_db_name)
        self.failUnless(int(sqlite_file.headers.dict['content-length']) > 0)
        self.failUnless(sqlite_file.headers.dict['content-type'] == 'application/octet-stream')
        self.failUnless(sqlite_file.headers.dict['content-disposition'] == 'attachment; filename=%s.sqlite' % self.populate_db_name)
        
        # Perform common tests on different types of api output formats
        self._datastore_api_response_check('jsondict')
        self._datastore_api_response_check('jsonlist')
        self._datastore_api_response_check('csv')
        self._datastore_api_response_check('htmltable')

        # RSS uses very different queries because of required column names
        rss2_response = self._get_data(type='rss2', scraper=self.populate_db_name, content_type='application/rss+xml; charset=utf-8',
                                        query="select a as title, b as link, c as description, d as guid, datetime(julianday('now'+key)) as pubDate from swdata limit 20").read()
        rss2_vals = re.findall('<item><title>[a-z0-9\-]*</title><link>[a-z0-9\-]*</link><description>[a-z0-9\-]*</description>' + 
                               '<guid isPermaLink="true">[a-z0-9\-]*</guid><(?:pubDate)|(?:date)>[a-z0-9\-]*</(?:pubDate)|(?:date)></item>', rss2_response)
        self.failUnless(len(rss2_vals)==20)
        rss2_response = self._get_data(type='rss2', scraper=self.populate_db_name, content_type='application/rss+xml; charset=utf-8',
                                        query="select a as title, b as link, c as description, datetime(julianday('now'+key)) as date from swdata limit 6").read()
        rss2_vals = re.findall('<item><title>[a-z0-9\-]*</title><link>[a-z0-9\-]*</link><description>[a-z0-9\-]*</description>' + 
                               '<guid isPermaLink="true">[a-z0-9\-]*</guid><(?:pubDate)|(?:date)>[a-z0-9\-]*</(?:pubDate)|(?:date)></item>', rss2_response)
        self.failUnless(len(rss2_vals)==6)  
        
        
    def _advanced_datastore_query(self):
        """ Do some more complicated tests on the datastore api
        Includes attachments and insert/drop queries """
        # TODO: check a join works properly
        # Make sure a query on an attached database works
        scraper_name = self.populate_db_name
        self._setup_db(filename = "python_scraper.txt")
        attach_response = self._get_data("jsondict", scraper_name, "select * from "+self.populate_db_name+".swdata", self.populate_db_name)
        attach_result = json.loads(attach_response.read())
        self.failUnless(attach_result == [{"td":"hello"},{"td":"world"}])
        # Check queries to write data
        query_response = self._get_data("jsondict", scraper_name, "drop table swdata")
        self.failUnless(json.loads(query_response.read()) == {"error": "sqlite3.Error: not authorized"}) 
        query_response = self._get_data("jsondict", scraper_name, "insert into swdata values (test)")
        self.failUnless(json.loads(query_response.read()) == {"error": "sqlite3.Error: not authorized"}) 
        
        
    def _datastore_api_response_check(self, format):
        """ Get some data from the datastore api and check the response is as expected """
        # Format specific information
        format_dict = { 
                        "jsondict":{  'content_type':'application/json; charset=utf-8',   'load':(lambda r:json.loads(r.read())), 
                                      'keys':(lambda v:v[0]),                             'num_results':(lambda v:len(v))            }, 
                        "jsonlist":{  'content_type':'application/json; charset=utf-8',   'load':(lambda r:json.loads(r.read())), 
                                      'keys':(lambda v:v['keys']),                        'num_results':(lambda v:len(v['data']))    },
                        "csv":{       'content_type':'text/csv',                          'load':(lambda r:csv.DictReader(r)), 
                                      'keys':(lambda v:v.fieldnames),                     'num_results':(lambda v:len(list(v)))      },
                        "htmltable":{ 'content_type':'text/html',                         'load':(lambda r:r.read()), 
                                      'keys':(lambda v:re.findall("<th>(.*?)</th>",v)),   'num_results':(lambda v:v.count('<tr>')-1) }
                      }
        # Values as expected from the loaded script in _setup_db
        keys = ['key','a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
        limit_keys = ['key','1','2']
        records = 20
        limit_records = 6
        # Perform a test for each set of values in the list below
        query_expected_records =[("select * from swdata", records, keys), 
                                ("select key, a as '1', b as '2' from swdata limit " + str(limit_records), limit_records, limit_keys)]
        
        for item in query_expected_records:
            # Load the raw api response
            response = self._get_data(type=format, scraper=self.populate_db_name, content_type=format_dict[format]['content_type'], query=item[0])
            # Load the response into a format-specific structure
            vals = format_dict[format]['load'](response)
            # Check the number of rows returned is as expected
            self.failUnless(format_dict[format]['num_results'](vals) == item[1])
            # Verify the column names are correct
            for key in format_dict[format]['keys'](vals):
                item[2].remove(key)
            self.failUnless(item[2] == [])
            
            
    def _get_data(self, type, scraper, query, attach=None, content_type=None):
        """ Send a post request to the datastore api and return a response object """
        params = {
                    "format" : type,
                    "name": scraper,
                    "query" : query
                 }
        if attach:
            params['attach'] = attach
        response = urllib2.urlopen(self.api_base + "datastore/sqlite?" + urllib.urlencode(params))
        # Check the content type (where specified) and content disposition where appropriate
        if type == "jsondict" or type == "jsonlist":
            self.failUnless(response.headers.dict['content-disposition'] == "attachment; filename=" + scraper + ".json" )
        elif type == "csv":
            self.failUnless(response.headers.dict['content-disposition'] == "attachment; filename=" + scraper + ".csv" )
        if content_type:
            self.failUnless(response.headers.dict['content-type'] == content_type)
        return response
        
        
    def _get_info(self, scraper, version="-1", history_start_date="", quietfields=""):
        """ Send a post request to the scraper info api and return json """
        params = {
                    "name" : scraper,
                    "version" : version,
                    "history_start_date": history_start_date,
                    "quietfields" : quietfields
                 }
        for param in params.keys():
            if not params[param]:
                del(params[param])
        response = urllib2.urlopen(self.api_base + "scraper/getinfo?" + urllib.urlencode(params))
        self.failUnless(response.headers.dict['content-disposition'] == "attachment; filename=scraperinfo.json" )
        self.failUnless(response.headers.dict['content-type'] == 'application/json; charset=utf-8')
        return json.loads(response.read())
        
    
    def _get_api_base(self):
        """ Get url of main site and apis """
        s = self.selenium
        
        s.open("/")
        self.wait_for_page()
        self.site_base = s.get_location()

        s.open("/docs/api#sqlite")
        self.wait_for_page()
        html = s.get_html_source()
        self.api_base = re.search('id="id_api_base" value="(?P<api_base>http[s]?://[^"]*)', html).group('api_base')
        
        
    def _set_api_key(self, entity_type, entity_name):
        """ Set the api key of either a 'scraper' or a 'user'. Entity name must be the short name of a scraper
        or username of a user """
        s = self.selenium
        self.user_login(SeleniumTest._adminuser['username'], SeleniumTest._adminuser['password'])
        api_key = str(uuid.uuid4())
        if entity_type == 'scraper':
            s.open("/admin/codewiki/scraper/?q=" + entity_name)
            apikey_element_id = "id_access_apikey"
        elif entity_type == 'user':
            s.open("/admin/auth/user/?q=" + entity_name)
            apikey_element_id = "id_userprofile_set-0-apikey"
        self.wait_for_page()
        s.click('link=' + entity_name)
        self.wait_for_page()
        s.type(apikey_element_id, api_key)
        s.click("//div[@class='submit-row']/input[@value='Save']")
        self.wait_for_page()
        self.user_login(self.user_name, self.user_pass)
        self.wait_for_page()
        return api_key
        
    
    def _setup_db(self, filename="populate_db_scraper.txt"):
        """ Initial setup of a sample scraper for querying in the API """
        s = self.selenium
        s.open("/")
        self.wait_for_page()
        
        populate_db_file = open(os.path.join( os.path.dirname( __file__ ), 'sample_data/' + filename))
        populate_db_code = populate_db_file.read().replace('&','&amp').replace('<','&lt').replace('>','&gt').replace('\n', '<br>')
        populate_db_file.close()
        
        self.user_pass = str( uuid.uuid4() )[:18].replace('-', '_')
        self.user_name = self.create_user(name="test user", password = self.user_pass)
        
        self.populate_db_name = self.create_code("python", code_type='scraper', code_source=populate_db_code)
        
        # Assume scraper run will be successful, only do basic completion checking
        run_enabled = "selenium.browserbot.getCurrentWindow().document.getElementById('run').disabled == false"
        s.wait_for_condition(run_enabled, 10000)
        s.click('run')
        seconds = 20
        while not (s.is_text_present('Starting run ...') and s.is_text_present('runfinished')):
            if seconds == 0:
                self.fail()
            seconds = seconds -1
            time.sleep(1)
        if not self.selenium.is_text_present('seconds elapsed'):
            self.fail()
            