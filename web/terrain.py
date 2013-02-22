import os
import sys
import shutil
import glob

from lettuce import before,after,world
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.core.management import call_command 
from django.test.client import Client
from django.utils.importlib import import_module
from django.http import HttpRequest
from django.db import DatabaseError
from south.management.commands import *
from splinter.browser import Browser
from selenium.webdriver.support.ui import WebDriverWait

@before.harvest
def sync_db(variables):
    if getattr(settings, 'LETTUCE_TESTING', False):
        patch_for_test_db_setup()
        call_command('syncdb', interactive=False, verbosity=0)

@before.harvest
def set_browser(variables):
    #world.browser = Browser('chrome')
    world.browser = Browser()

@after.harvest
def close_browser(totals):
    failed = False
    for total in totals:
        if total.scenarios_ran != total.scenarios_passed:
            failed = True
    if not failed:
        world.browser.quit()

@after.each_step
def take_screenshot_if_error(step):
    if step.failed:
        world.browser.driver.save_screenshot('/tmp/%s.png' % step.sentence)

@world.absorb
class FakeLogin(Client):
    def login(self, username, password):
        user = authenticate(username=username, password=password)
        if user and user.is_active \
                and 'django.contrib.sessions.middleware.SessionMiddleware' in settings.MIDDLEWARE_CLASSES:
            engine = import_module(settings.SESSION_ENGINE)
    
            request = HttpRequest()
            if self.session:
                request.session = self.session
            else:
                request.session = engine.SessionStore()
            login(request, user)
    
            request.session.save()
    
            cookie_data = {
                    'name'    : settings.SESSION_COOKIE_NAME,
                    'value'   : request.session.session_key,
                    'max-age' : None,
                    'path'    : '/',
                    #'domain'  : settings.SESSION_COOKIE_DOMAIN,
                    'expires' : None,
                    }
            return cookie_data
        else:
            raise Exception("Couldn't authenticate")

@world.absorb
def wait_for_fx(timeout=5):
    WebDriverWait(world.browser.driver, timeout).until(lambda _d:
      world.browser.evaluate_script('jQuery.queue("fx").length == 0'))

@world.absorb
def wait_for_ajax(timeout=5):
    WebDriverWait(world.browser.driver, timeout).until(lambda _d:
      world.browser.evaluate_script('jQuery.active == 0'))

@world.absorb
def disable_fx():
    world.browser.execute_script('jQuery.fx.off = true')

@world.absorb
def wait_for_element_by_css(css, timeout=5):
    WebDriverWait(world.browser.driver, timeout).until(lambda _d:
      len(world.browser.find_by_css(css)) != 0)

@world.absorb
def wait_for_url(url, timeout=5):
    WebDriverWait(world.browser.driver, timeout).until(lambda _d:
      (url in world.browser.url))

@before.each_scenario
def load_data(variables):
    try:
        call_command('flush', interactive=False)
    except DatabaseError:
        pass # This will occur if the tests are run for the first time

    call_command('loaddata', 'test-fixture.yaml')

# Because Django is threaded, and the way Lettuce coopts the subprocess, we can't
# use the normal mail.outbox in tests to get to emails. Instead we use the
# filebased backend, and some special functions here.
#   https://github.com/gabrielfalcao/lettuce/issues/215
# We need to override both before everything, and each request, don't really know why.
@before.harvest
def override_mail_settings_before_all(variables):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    settings.EMAIL_FILE_PATH = '/tmp/sw_lettuce_terrain_emails'
@before.handle_request
def override_mail_settings(httpd, server):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    settings.EMAIL_FILE_PATH = '/tmp/sw_lettuce_terrain_emails'
# Clear the mails out each scenario
@before.each_scenario
def override_mail_settings_before_scenario(scenario):
    if not os.path.isdir(settings.EMAIL_FILE_PATH):
        os.mkdir(settings.EMAIL_FILE_PATH)
    for f in glob.glob(settings.EMAIL_FILE_PATH + "/*.log"):
        os.unlink(f)

@world.absorb
def mails_len():
    if os.path.exists(settings.EMAIL_FILE_PATH):
        return len(glob.glob(settings.EMAIL_FILE_PATH + "/*.log"))
    else:
        return 0

@world.absorb
def mails_file():
    mailfiles = glob.glob(settings.EMAIL_FILE_PATH + "/*.log")
    sorted_mailfiles = sorted(mailfiles, key=lambda p: os.stat(p).st_mtime)
    return sorted_mailfiles

@world.absorb
def mails_body():
    return map(lambda f: open(f).read(), world.mails_file())
   
# Not currently used
def clear_obscuring_popups(browser):
    """Clear alerts and windows that would otherwise obscure buttons.
    """

    for id in ["djHideToolBarButton", "alert_close"]:
        elements = browser.find_by_id(id)
        if not elements:
            continue
        element = elements.first
        if element.visible:
            element.click()

