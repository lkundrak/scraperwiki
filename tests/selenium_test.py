import unittest
import atexit
from selenium import selenium
import uuid, time

# XXX make this a static member
def SeleniumTest_atexit():
    SeleniumTest._selenium.stop()

class SeleniumTest(unittest.TestCase):

    _valid_username = ''
    _valid_password = ''    

    _selenium_host = ''
    _selenium_port = 4444
    _selenium_browser = None

    _selenium = None

    _app_url = ''

    _verbosity = 1

    def setUp(self):
        self.verificationErrors = []

        # make singleton Selenium connection and new browser window
        if SeleniumTest._selenium == None:
            SeleniumTest._selenium = selenium(SeleniumTest._selenium_host, SeleniumTest._selenium_port, 
                                     SeleniumTest._selenium_browser, SeleniumTest._app_url)
            SeleniumTest._selenium.start()

            # make sure we quit the selenium when the script dies
            atexit.register(SeleniumTest_atexit)
        self.selenium = SeleniumTest._selenium
        self.selenium.delete_all_visible_cookies()
        #do_command('deleteAllCookies', [])
            
        # extract a title for the job from name of test.  must be done in the constructor or after start()
        self.selenium.set_context("sauce:job-name=%s" % self._testMethodName)  
        self.selenium.window_maximize()
        
        # If we have the dev toolbar, get rid of it to prevent interference.
        self.hide_dev_toolbar()

    def hide_dev_toolbar(self):
        s = self.selenium
        s.open("/")
        self.wait_for_page()
        if s.is_element_present("djHideToolBarButton"): 
            if s.is_visible("djHideToolBarButton"):
                s.click("djHideToolBarButton")
        
        
    def wait_for_page(self, doing=None):
        hit_limit = True
        # DO NOT call anything else (even for debugging, e.g. self.selenium.get_location) at this point as:
        # "Running any other Selenium command after turns the flag to false."
        # http://release.seleniumhq.org/selenium-remote-control/0.9.2/doc/dotnet/Selenium.DefaultSelenium.WaitForPageToLoad.html
        try:
            self.selenium.wait_for_page_to_load('30000')
            hit_limit = False
        except:
            print 'Failed to load page in first 30 seconds, adding another 30'
        
        if hit_limit:
            try:
                self.selenium.wait_for_page_to_load('30000')
                hit_limit = False
            except:
                if not doing:
                    msg = 'It took longer than 60 seconds to visit %s, it may have failed' % self.selenium.get_location()
                else:
                    msg = 'It took longer than 60 seconds to: %s' % doing
                self.fail(msg=msg)

        if self._verbosity > 1:
            print "  waiting_for_page done, now at", self.selenium.get_location()                  
        
    def type_dictionary(self, d):
        for k,v in d.iteritems():
            self.selenium.type( k, v )
        
    def tearDown(self):
        self.assertEqual([], self.verificationErrors)





    def create_user(self, name="test user", password = str( uuid.uuid4() )[:18].replace('-', '_') ):
        s = self.selenium
        s.open("/logout")
        self.wait_for_page()
        s.click( "link=Log in" )
        self.wait_for_page()
    
        username = "se_test_%s" % str( uuid.uuid4() )[:18].replace('-', '_')
    
        d = {}
        d["id_name"] = name
        d["id_username"] = username
        d["id_email"] = "%s@scraperwiki.com" % username
        d["id_password1"]  = password
        d["id_password2"]  = password
        
        self.type_dictionary( d )
        s.click( 'id_tos' )
        s.click('register')
        self.wait_for_page()
        
        self.failUnless(s.is_text_present("Your dashboard"), msg='User is not signed in and should be')
    
        return username


    def create_code(self, language, code_type, code_source, view_attach_scraper_name = ''):
        code_name = 'se_test_%s' % str( uuid.uuid4() )[:18].replace('-', '_')
        
        s = self.selenium
        
        s.open('/dashboard/')
        self.wait_for_page()
        
        s.answer_on_next_prompt( code_name )        
        s.click('//a[@class="editor_%s"]' % code_type)        
        time.sleep(1)
        link_name = { "python":"Python", "ruby":"Ruby", "php":"PHP" }[language]
        s.click("//a[text()=' %s ']" % link_name )
        self.wait_for_page()
    
        # Prompt and wait for save button to activate
        s.type_keys('//body[@class="editbox"]', "\16")
        s.wait_for_condition("selenium.browserbot.getCurrentWindow().document.getElementById('btnCommitPopup').disabled == false", 10000)
        
        # Load the scraper/view code and insert directly into page source, inserting the attachment scraper name if a view
        if code_type == 'view':
            code_source = code_source.replace('{{sourcescraper}}', view_attach_scraper_name)
        s.type('//body[@class="editbox"]', "%s" % code_source)
    
        s.click('btnCommitPopup')
        self.wait_for_page()
        time.sleep(1)
        
        return code_name

    def set_code_privacy(self, privacy, code_type, code_name = '', owner = {}):
        """ 
        Set the currently open scraper/view to be the specified privacy. Assumes a
        Django admin account has been specified if setting as private. Needs
        code_name and the owner account if setting as private.
        """
        privacy_set = "selenium.browserbot.getCurrentWindow().document.getElementById('privacy_status').children[0].style.display != 'none'"
        s = self.selenium
        if privacy == 'public' or privacy == 'protected':
            s.click('show_privacy_choices')
            s.click('privacy_' + privacy)
            s.wait_for_condition(privacy_set, 10000)
            self.failUnless(s.is_text_present("This %s is " % code_type + privacy))
        elif privacy == 'private':
            self.user_login(SeleniumTest._adminuser['username'], SeleniumTest._adminuser['password'])
            s.open(("/admin/codewiki/%s/?q=" % code_type) + code_name)
            self.wait_for_page()
            s.click('link=' + code_name)
            self.wait_for_page()
            s.select("id_privacy_status", "label=Private")
            s.click("//input[@value='Save']")
            self.wait_for_page()
            self.user_login(owner['username'], owner['password'])
            s.open("/%ss/" % code_type + code_name)
            self.wait_for_page()
            self.failUnless(s.is_text_present("This %s is private" % code_type))
        else:
            self.fail()

    def add_code_editor(self, username, expected_msg):
        """ 
        Set the specified username as an editor on the currently open scraper/view summary page.
        Assumes the current user has permissions to do so and that the scraper/view is private/public.
        """
        error_showing = "selenium.browserbot.getCurrentWindow().document.getElementById('contributorserror').style.display != 'none'"
        finished_loading = "selenium.browserbot.getCurrentWindow().document.getElementById('contributors_loading').style.display == 'none'"
        add_editor_visible = "selenium.browserbot.getCurrentWindow().document.getElementById('addneweditor').children[1].style.display != 'none'"
        
        s = self.selenium
        s.click("link=Add a new editor")
        s.type("//div[@id='addneweditor']/span/input[@role='textbox']", username)
        s.click("xpath=//div[@id='addneweditor']/span/input[@class='addbutton']")
        s.wait_for_condition(error_showing + " || (" + finished_loading + " && " + add_editor_visible + ")", 10000)
        self.failUnless(s.is_text_present(expected_msg))
        
    def user_login(self, username, password):
        """ Logout if already logged in and log back in as specified user """
        s = self.selenium
        # Pause here to force sync and bypass intermittent issues such 
        # as blank JS alerts interrupting selenium and logout failure
        time.sleep(2)
        s.open("/logout")
        self.wait_for_page()
        time.sleep(2) # likewise
        s.type('id_nav_user_or_email', username)
        s.type('id_nav_password', password)
        s.click('nav_login_submit')
        self.wait_for_page()
    
    def activate_users(self, userlist):
        """ 
        Set all usernames in userlist to be activated. Requires Django admin account to be specified 
        and for alert types to have been set up.
        """
        s = self.selenium
        self.user_login(SeleniumTest._adminuser['username'],SeleniumTest._adminuser['password'])
        
        for username in userlist:
            s.open("/admin/auth/user/?q=" + username)
            self.wait_for_page()
            s.click("link=" + username)
            self.wait_for_page()
            s.click("id_is_active")
            s.click("//div[@class='submit-row']/input[@value='Save']")
            self.wait_for_page()