from lettuce import *
from lettuce.django import django_url

PAGES = {
        "home":                         "/",
        "login":                        "/login/",
        "contact":                      "/contact/",
        "pricing":                      "/pricing/",
        "individual payment":           "/subscribe/individual/",
        "business payment":             "/subscribe/business/",
        "corporate payment":            "/subscribe/corporate/",
        "vaults":                       "/vaults/",
        "new vault":                    "/vaults/new/",
        "python scraper code editing":  "/scrapers/new/python", 
        }

def page_name_is_valid(name):
    assert PAGES.has_key(name), \
        'the page "%s" is not mapped in the PAGES dictionary, ' \
        'check if you misspelled it or add into it' % name
    return True

@step(u'(?:(?:Given|And) I am on|When I visit) the (.+) page')
def when_i_visit_the_pricing_page(step, name):
    response = world.browser.visit(django_url(PAGES[name]))

@step(u'(?:And|Then) I should be on the (.+) page')
def then_i_should_be_on_the_payment_page(step, name):
    assert page_name_is_valid(name)
    current_url = world.browser.url.split('?')[0].split('#')[0] #ignore querystring & anchor: hacky
    full_url = django_url(PAGES[name])

    assert current_url == full_url, \
            'the current url is "%s" but should be "%s"' % (current_url, full_url)

    world.wait_for_url(full_url)
