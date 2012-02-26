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
        try:
            call_command('flush', interactive=False)
        except DatabaseError:
            pass # This will occur if the tests are run for the first time
        call_command('syncdb', interactive=False, verbosity=0)
        call_command('loaddata', 'test-fixture.yaml')

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
def wait_for_element_by_css(css, timeout=5):
    WebDriverWait(world.browser.driver, timeout).until(lambda _d:
      len(world.browser.find_by_css(css)) != 0)

@world.absorb
def wait_for_url(url, timeout=5):
    WebDriverWait(world.browser.driver, timeout).until(lambda _d:
      (url in world.browser.url))
   
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

