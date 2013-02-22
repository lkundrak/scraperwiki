from lettuce import *
from lettuce.django import django_url

PAGES = {
        'home':                         '/',
        'search test':                  '/search/test/',
        'testalicious tag':             '/tags/testalicious',
        'login':                        '/login/',
        'sign up':                      '/login/',
        'contact':                      '/contact/',
        'help':                         '/help/',
        'pricing':                      '/pricing/',
        'individual payment':           '/subscribe/individual/',
        'business payment':             '/subscribe/business/',
        'corporate payment':            '/subscribe/corporate/',
        'vaults':                       '/vaults/',
        'new vault':                    '/vaults/new/',
        'python scraper code editing':  '/scrapers/new/python', 
        'public request':               '/request_data/#public', 
        'request':                      '/request_data/', 
        'corporate home':               '/corporate/',
        'corporate features':           '/corporate/features/',
        'corporate contact':            '/corporate/contact/',
        'corporate contact thanks':     '/corporate/contact/thanks',
        'edit profile':                 '/profiles/edit/'
        }

def page_name_is_valid(name):
    assert PAGES.has_key(name), \
        'the page "%s" is not mapped in the PAGES dictionary, ' \
        'check if you misspelled it or add into it' % name
    return True

@step(u'(?:(?:Given|And) I am on|(?:When|And) I visit) the (.+) page')
def when_i_visit_the_particular_page(step, name):
    response = world.browser.visit(django_url(PAGES[name]))

@step(u'(?:And|Then) I should be on the (.+) page')
def then_i_should_be_on_the_particular_page(step, name):
    assert page_name_is_valid(name)
    current_url = world.browser.url.split('?')[0] # ignore querystring (hacky)

    if '#' not in PAGES[name]:
        # Ignore querystring if not in page URL.
        current_url = current_url.split('#')[0]

    full_url = django_url(PAGES[name])

    assert current_url == full_url, \
            'the current url is "%s" but should be "%s"' % (current_url, full_url)

    world.wait_for_url(full_url)
