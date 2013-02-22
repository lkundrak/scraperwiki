from lettuce import *
from django.contrib.auth.models import User
from frontend.models import UserProfile, Feature
from selenium.webdriver.support.ui import WebDriverWait

@step(u'(?:Given|And) I have ([a0-9]) vaults?$')
def i_have_a_vault(step, num):
    if num == 'a':
        num = 1
    num = int(num)
    user = User.objects.get(username='test')
    profile = user.get_profile()

    for i in range(num):
        profile.create_vault('My #%d Vault' % (i+1))

@step(u'(?:Given|And) my vault contains (a|\d+) scrapers?$')
def my_vault_contains_x_scrapers(step, num):
    from codewiki.models import Vault, Scraper, UserCodeRole
    user = User.objects.get(username='test')
    vault = [v for v in user.vaults.all()][0]
    num = 1 if num=='a' else int(num)
    for i in range(num):
        scraper = Scraper()
        scraper.title = u'Private Scraper #%s' % (i+1)
        scraper.language = u'python'
        scraper.privacy_status = u'private'
        scraper.vault = vault
        scraper.generate_apikey()
        scraper.save()
        vault.update_access_rights()
        scraper.commit_code(u"import scraperwiki\n\n# Blank Python\n\n", u"Created", user)

@step(u'(?:Given|And) my vault contains a scraper called "([^"]*)"$')
def my_vault_contains_a_scraper_called_x(step, title):
    from codewiki.models import Vault, Scraper, UserCodeRole
    user = User.objects.get(username='test')
    vault = [v for v in user.vaults.all()][0]
    scraper = Scraper()
    scraper.title = title
    scraper.language = u'python'
    scraper.privacy_status = u'private'
    scraper.vault = vault
    scraper.generate_apikey()
    scraper.save()
    vault.update_access_rights()
    scraper.commit_code(u"import scraperwiki\n\n# Blank Python\n\n", u"Created", user)

# This actually only checks that I can see *any* empty vault
# Not neccessarily that the empty vault is *new*
@step(u'(?:Then|And) I should see a new empty vault')
def i_should_see_a_new_empty_vault(step):
    assert world.browser.find_by_css('div.vault_contents.empty')

@step(u'(?:Then|And) I should not see a new empty vault')
def i_should_not_see_a_new_empty_vault(step):
    assert not world.browser.find_by_css('div.vault_contents.empty')

@step(u'(?:Then|And) I should see (a|\d+) scrapers?$')
def i_should_see_x_scrapers(step, num):
    num = 1 if num=='a' else int(num)
    assert len(world.browser.find_by_css('li.code_object_line'))==num

# We should work out how to test 'hacks' like this
# DRJ suggests not testing them using Lettuce?
@step(u'When I make an AJAX request to the endpoint "([^"]*)"')
def when_i_make_an_ajax_request_to_the_endpoint(step, url):
    assert True
    
@step(u'Then I should not be successful')
def then_i_should_not_be_successful(step):
    assert True
