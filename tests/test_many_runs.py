import os, sys, unittest, uuid, time, re
from selenium import selenium
from selenium_test import SeleniumTest
from urlparse import urlparse


class TestManyRuns(SeleniumTest):

    def login_manyrunsuser(self):
        s = self.selenium
        s.open("/logout")
        s.click("link=Log in")
        self.wait_for_page()

        username = "manyrunuser"
        password = "MANYRUNUSER"
        
        dlog = { "css=#id_user_or_email":username, "css=#id_password":password }
        dreg = { "css=#id_name":username, "css=#id_username":username, "css=#id_email":"%s@scraperwiki.com" % username, "css=#id_password1":password, "css=#id_password2":password }
        
        s.type("css=#divContent #id_user_or_email", username)
        s.type("css=#divContent #id_password", password)
        time.sleep(2)
        s.click('css=#divContent #login_form input:submit')
        self.wait_for_page()
        time.sleep(2)
        if s.is_text_present('Sorry, but we could not find that user'):
            self.type_dictionary(dreg)
            s.click('css=#id_tos')
            s.click('register')
            self.wait_for_page()

        time.sleep(8)
        self.failUnless(s.is_text_present("Logged in"), msg='User is not signed in and should be')


    def test_many_runs(self):  
        s = self.selenium
        self.login_manyrunsuser()
    
        # find all the runners
        s.open("/search/manyrunnerscript/")
        time.sleep(1)
        bodytext = s.get_body_text()
        manyrunnerindex = set([int(i)  for i in re.findall("manyrunnerscript_(\d+)\s", bodytext)])
        print manyrunnerindex
        scraper_count = s.get_css_count('css=li.code_object_line')
        print "number of manyrunnerscripts", scraper_count
        
        # manufacture more runner scripts if necessary
        bcode = """
import scraperwiki, time, urllib\r
x=1\r
print len(urllib.urlopen("http://api.dev.scraperwiki.com/api/1.0/scraper/getinfo?name=manyrunnerscript_%d").read())
for i in range(%d):\r
    for j in range(1, %d00):\r
        x*=j\r
    scraperwiki.sqlite.save(["i"], {"i":i, "x":len(str(x))})\r
    time.sleep(i*0.1+7)
    print i
print "done", i, len(str(x))
"""
        while len(manyrunnerindex) < 30:
            i = max(manyrunnerindex) + 1
            link_name = 'Python scraper'
            
            scriptname = "manyrunnerscript_%d" % i
            s.answer_on_next_prompt(scriptname)
            print "Making", scriptname
            s.open("/scrapers/new/python#plain")
            code = bcode % (i, i, i)
            code = "print '888',\r\n"*100+code   # bunch of junk at the top
            s.type('css=#id_code', code)
            time.sleep(1)
            s.click('btnCommitPopup')
            self.wait_for_page()
            s.click('aCloseEditor1')
            self.wait_for_page()
            manyrunnerindex.add(i)

        # go in and set each one running (many user must be staff status to do this)
        for i in list(manyrunnerindex)[:22]:
            s.open("/scrapers/manyrunnerscript_%d/" % i)
            if s.get_css_count('css=#btnScheduleScraper'):
                s.click("btnScheduleScraper")
                self.wait_for_page()
            s.click("btnRunScraper")
            self.wait_for_page()

