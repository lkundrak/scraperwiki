import os, sys, unittest, uuid, time
from selenium import selenium
from selenium_test import SeleniumTest
from urlparse import urlparse
import urllib2
from BeautifulSoup import BeautifulSoup
import lxml.html
from selenium.webdriver.common.keys import Keys

class TestScrapers(SeleniumTest):
    """
    Creates and runs some scrapers in the three main supported languages. 
    
    Create
    Run
    Check
    
    Also checks some language-independant features including privacy and
    comments.
    """
    
    # TODO:
    # Add more comprehensive views tests - currently only does very basic generation check
    #    Check content type header is set correctly

    def test_ruby_create(self):
        self._language_create("ruby")

    def test_php_create(self):
        self._language_create("php")

    def test_python_create(self):
        self._language_create("python")

    def test_common_features_scraper(self):
        self._common_create('scraper')

    def test_common_features_view(self):
        self._common_create('view')
        
    def _load_data(self, language, obj):
        thefile = os.path.join( os.path.dirname( __file__ ), 'sample_data/%s_%s.txt' % (language, obj,))
            
        f = open(thefile)
        # The file seems to be directly inserted into the source of the page, so some characters need
        # to be html encoded.
        code = f.read().replace('&','&amp').replace('<','&lt').replace('>','&gt').replace('\n', '<br>')
        f.close()
    
        return code
        
    def _load_view_html(self, scraper_name):
        return [('<head>\n</head>\n<body>\n <h2>\n  Some data from scraper: %s  (1 columns)\n </h2>' % scraper_name),
                '<table style="border-collapse:collapse;" border="1">\n  <tbody>\n   <tr>\n    <th>\n     td\n    </th>\n   </tr>' + 
                '\n   <tr>\n    <td>\n     hello\n    </td>\n   </tr>\n   <tr>\n    <td>\n     world\n    </td>\n   </tr>\n  </tbody>\n </table>']

    
    def _add_comment(self, code_name, code_type):
        s = self.selenium
              
        self.failUnless(s.is_text_present('This scraper has no chat'))

        comment = 'A test comment'

        s.type('id_comment', comment)
        s.click('id_submit')
        self.wait_for_page()

        self.failUnless(s.is_text_present(comment))
        self.failUnless(s.is_text_present("regexp:This\s+scraper's\s+chat"))

        
    def _check_dashboard_count(self, count=2):
        """ 
        Go to the current user's dashboard and verify the 
        number of scrapers there 
        """
        s = self.selenium
                
        s.click('link=Your dashboard')
        self.wait_for_page()
        
        scraper_count = int(s.get_xpath_count('//li[@class="code_object_line"]'))    
        self.failUnless( count == scraper_count, msg='There are %s items instead of %s' % (scraper_count,count,) )
        

    def _check_clear_recover_data(self, scraper_name):
        s = self.selenium     
                
        s.open('/scrapers/%s/' % scraper_name)        
        self.wait_for_page()  
        # Clear the datastore
        s.click('btnClearDatastore')
        self.wait_for_page()
        self.failUnless(s.is_text_present( 'Your data has been deleted' ))
        self.failIf(s.is_text_present( 'This dataset has a total of' ))
        # Recover the datastore
        s.click("link=Undo?")
        self.wait_for_page()
        self.failUnless(s.is_text_present( 'Your data has been recovered' ))
        self.failUnless(s.is_text_present( 'This dataset has a total of' ))
        # Delete it again
        s.click('btnClearDatastore')
        self.wait_for_page()
        self.failUnless(s.is_text_present( 'Your data has been deleted' ))
        self.failIf(s.is_text_present( 'This dataset has a total of' ))


    def _check_delete_code(self, code_name, code_type):
        s = self.selenium
        s.open('/%ss/%s/' % (code_type, code_name))
        self.wait_for_page('view the %s page so we can delete it' % code_type)                
        s.click('btnDeleteScraper')
        self.wait_for_page('Your %s has been deleted' % code_type)
        
        if s.is_text_present('Exception Location'):
            print s.get_body_text()
            self.fail('An error occurred deleting data')
        elif s.is_text_present(code_name):
            self.fail('%s was not deleted successfully' % code_type)
        
        self.assertEqual('/dashboard/', urlparse(s.get_location()).path, 'Did not redirect to dashboard after deleting %s' % code_type)


    def _wait_for_run(self):
        """ We'll click run and then wait for 3 seconds, each time checking 
            whether we have in fact finished.  
        """
        s = self.selenium
        
        run_enabled = "selenium.browserbot.getCurrentWindow().document.getElementById('run').disabled == false"
        s.wait_for_condition(run_enabled, 10000)
        s.click('run')
        success,total_checks,reconnects = False, 12, 1

        # Dev server is slow, allow a page refresh on problems and give a longer timeout (allow https or http)
        if "dev.scraperwiki.com" in s.browserURL:
            reconnects = 5
            total_checks = 40

        while not (s.is_text_present('Starting run ...') and s.is_text_present('runfinished')):
            if total_checks == 0 and reconnects == 0:
                self.fail('Running the scraper seemed to fail')
                return
            elif ((s.is_text_present('Connection to execution server lost') and (reconnects > 0))
                    or (s.is_text_present('runfinished') and not s.is_text_present('Starting run') and (reconnects > 0))
                    or (total_checks == 0) and (reconnects > 0)):
                # Refresh and start anew, something went wrong
                s.refresh()
                self.wait_for_page()
                time.sleep(1)
                s.wait_for_condition(run_enabled, 10000)
                s.click('run')
                reconnects -= 1
                total_checks = 40
            time.sleep(3)
            total_checks -= 1
            
        if self.selenium.is_text_present('seconds elapsed'):
            # If the scraper has executed check that we have the expected output
            self.failUnless( s.is_text_present('hello') and s.is_text_present('world') ) 
            self.failIf( s.is_text_present('Traceback') )
            success = True
            print 'Scraper returned some data!!!'
        
        self.failUnless(success)
        

    # searches specific markup currently used for the contributor list, to pull
    # out what status they have
    def _find_contributor_status(self, s, hunt_for_user_name):
        root = lxml.html.fromstring(s.get_html_source())
        for el in root.cssselect("ul#contributorslist li"):
            user_name = el.cssselect("img")[0].tail.strip() # text of user name is just after first image (their profile photo)
            if len(el.cssselect("img.vault_owner_flash")) > 0: # they are marked with a diagonal flash image
                status = 'owner'
            else:
                status = 'editor'

            if user_name == hunt_for_user_name:
                return status
        return None


    def _editor_demote_self(self, code_name, code_type, owner, editor):
        """ 
        Get the 'editor' account to demote themselves from 
        being an editor of 'code_name', then login as 'owner'
        """
        s = self.selenium
        self.user_login(editor['username'], editor['password'])
        s.open("/%ss/%s/" % (code_type, code_name))
        self.wait_for_page()
        s.click("xpath=//input[@class='detachbutton']")
        self.assertEqual(self._find_contributor_status(s, editor['username']), None)
        self.user_login(owner['username'], owner['password'])
        s.open("/%ss/%s/" % (code_type, code_name))
        self.wait_for_page()


    def _check_editor_permissions(self, code_name, code_type, owner, editor, privacy, on_editor_list):
        """
        Check that the account 'editor' has the expected permissions for 'code_name', given
        the privacy setting of the scraper ('privacy') and whether they are on the editors list
        ('on_editor_list'), then log in as 'owner'.
        """
        s = self.selenium
        self.user_login(editor['username'], editor['password'])
        s.open("/dashboard")
        if on_editor_list:
            self.failUnless(s.is_text_present(code_name))
            s.open("/%ss/%s/edit/" % (code_type, code_name))
            self.wait_for_page()
            s.wait_for_condition("selenium.browserbot.getCurrentWindow().document.getElementById('protected_warning').style.display == 'none'", 10000)
            self.failIf(s.get_attribute('btnCommitPopup@style') == "display:none;")
        else:
            self.failIf(s.is_text_present(code_name))
            s.open("/%ss/%s/edit/" % (code_type, code_name))
            self.wait_for_page()
            if privacy == 'private':
                self.failUnless(s.is_text_present("Sorry, this %s is private" % code_type))
            elif privacy == 'protected':
                s.wait_for_condition("selenium.browserbot.getCurrentWindow().document.getElementById('btnCommitPopup').style.display == 'none'", 10000)
                # TODO: Check direct 'post'ing of data
            else:
                self.fail()
        self.user_login(owner['username'], owner['password'])
        s.open("/%ss/%s/" % (code_type, code_name))
        self.wait_for_page()
        

    def _check_editors_list_changes(self, code_name, code_type, owner, editor, privacy):
        """
        Perform possible combinations of actions with adding/removing editors and check
        that an editor user has the appropriate permissions at each stage.
        """
        s = self.selenium
        self._check_editor_permissions(code_name, code_type, owner, editor, privacy, False)
        # Add existing user as editor
        self.add_code_editor(editor['username'], "test %s_editor (editor)" % code_type)
        self._check_editor_permissions(code_name, code_type, owner, editor, privacy, True)
        # Try to add existing editor again
        self.add_code_editor(editor['username'], "test %s_editor (editor)" % code_type)
        self.failUnless("int(s.get_xpath_count('//ul[@id=\'contributorslist\']/li')) == 2")
        self._check_editor_permissions(code_name, code_type, owner, editor, privacy, True)
        # Try to add owner as editor
        self.add_code_editor(owner['username'], "Failed: user is already owner")
        s.click("xpath=//div[@id='addneweditor']/span/input[@class='cancelbutton']")
        # Try to add non-existent user as editor
        self.add_code_editor("se_nonexistent_user", "Failed: username 'se_nonexistent_user' not found")
        s.click("xpath=//div[@id='addneweditor']/span/input[@class='cancelbutton']")
        # Demote existing editor        
        self.failUnless("int(s.get_xpath_count('//input[@class=\"demotebutton\"]')) == 1")
        s.click("xpath=//input[@class='demotebutton']")
        self.assertEqual(self._find_contributor_status(s, editor['username']), None)
        self._check_editor_permissions(code_name, code_type, owner, editor, privacy, False)
        # Check editor demoting self from scraper
        self.add_code_editor(editor['username'], "test %s_editor (editor)" % code_type)
        self._check_editor_permissions(code_name, code_type, owner, editor, privacy, True)
        self._editor_demote_self(code_name, code_type, owner, editor)
        self._check_editor_permissions(code_name, code_type, owner, editor, privacy, False)


    def _check_code_privacy(self, code_name, code_type, owner, editor):
        """ Make sure different scraper privacy settings work as expected """
        s = self.selenium
        s.open("/%ss/" % code_type + code_name)
        self.wait_for_page()
        self.assertEqual(self._find_contributor_status(s, "test user"), "owner")
        # Set scraper protected and check editor permission changing
        self.set_code_privacy('protected', code_type)
        self._check_editors_list_changes(code_name, code_type, owner, editor, 'protected')
        
        # Check added user stays as follower when setting scraper public
        self.add_code_editor(editor['username'], "test %s_editor (editor)" % code_type)
        self.set_code_privacy('public', code_type)
        self.assertEqual(self._find_contributor_status(s, "test %s_editor" % code_type), "editor")
        self.failUnless("int(s.get_xpath_count('//input[@class=\"demotebutton\"]')) == 0")
        
        
    def _language_create(self, language):
        # Language specific tests
        s = self.selenium
        s.open("/logout")
        self.create_user()
        
        # Scraper creation and tests
        scraper_name = self.create_code(language, 'scraper', self._load_data(language, 'scraper'))
        self._wait_for_run()
        s.click('link=Scraper')
        self.wait_for_page()
        # Check for precreated e-mail scraper and new scraper
        self._check_dashboard_count()

        # View creation and test that generated html is as expected
        view_name = self.create_code(language, 'view', self._load_data(language, 'view'), scraper_name)
        s.open("/run/" + view_name)
        self.wait_for_page()
        for fragment in self._load_view_html(scraper_name):
            self.failUnless(fragment in BeautifulSoup(self.selenium.get_html_source()).prettify())
        # Clear up the evidence of testing
        self._check_clear_recover_data( scraper_name )
        self._check_delete_code( scraper_name, 'scraper' )
        self._check_delete_code( view_name, 'view' )        
        # Only e-mail scraper should be left
        self._check_dashboard_count(count=1)


    def _common_create(self, code_type):
        """ Perform a language-agnostic set of tests on a scraper """
        if not SeleniumTest._adminuser:
            print "Cannot perform some tests (including privacy tests) without a Django admin account specified"
        s = self.selenium
        owner = {'username':'', 'password':''}
        editor = {'username':'', 'password':''}
        owner['password'] = str( uuid.uuid4() )[:18].replace('-', '_')
        editor['password'] = str( uuid.uuid4() )[:18].replace('-', '_')
        s.open("/logout")
        editor['username'] = self.create_user(name="test %s_editor" % code_type, password=editor['password'])
        s.open("/logout")
        owner['username'] = self.create_user(password=owner['password'])
        code_name = self.create_code("python", code_type, self._load_data("python", code_type), '')
        s.click('link=Back to ' + code_type + ' overview')
        self.wait_for_page()

        # edit description
        s.click('css=.edit_description')
        s.type('css=#divAboutScraper textarea', "This is a changed description")
        s.click("//div[@id='divAboutScraper']//button[text()='Save']")
        time.sleep(1) # XXX how to wait just until the JS has run?
        self.failUnless(s.is_text_present("This is a changed description"))

        # edit tags
        s.click('css=.tag a')
        s.type('css=.new_tag_box input', "rabbit")
        s.key_press_native(10)
        time.sleep(1) # XXX how to wait just until the JS has run?
        self.failUnless(s.is_text_present("rabbit"))

        # comments
        self._add_comment(code_name, code_type)

        # privacy
        self.activate_users([owner['username'], editor['username']])
        self.user_login(owner['username'], owner['password'])
        self._check_code_privacy(code_name, code_type, owner, editor)

