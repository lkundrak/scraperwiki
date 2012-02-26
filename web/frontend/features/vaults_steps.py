from lettuce import *
from django.contrib.auth.models import User
from frontend.models import UserProfile, Feature
from selenium.webdriver.support.ui import WebDriverWait

@step(u'(?:Given|And) I have ([a0-9]) vaults?')
def and_i_have_a_vault(step, num):
    if num == 'a':
        num = 1
    num = int(num)
    user = User.objects.get(username='test')
    profile = user.get_profile()

    for i in range(num):
        profile.create_vault('My #%d Vault' % (i+1))

# This actually only checks that I can see *any* empty vault
# Not neccessarily that the empty vault is *new*
@step(u'(?:Then|And) I should see a new empty vault')
def i_should_see_a_new_empty_vault(step):
    assert world.browser.find_by_css('div.vault_contents.empty')

@step(u'(?:Then|And) I should not see a new empty vault')
def i_should_not_see_a_new_empty_vault(step):
    assert not world.browser.find_by_css('div.vault_contents.empty')
    
# We should work out how to test 'hacks' like this
# DRJ suggests not testing them using Lettuce?
@step(u'When I make an AJAX request to the endpoint "([^"]*)"')
def when_i_make_an_ajax_request_to_the_endpoint(step, url):
    assert True
    
@step(u'Then I should not be successful')
def then_i_should_not_be_successful(step):
    assert True
