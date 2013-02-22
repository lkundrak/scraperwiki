from lettuce import step,before,world
from django.contrib.auth.models import User
from lettuce.django import django_url

@step("When I click the login link")
def when_i_click_the_login_link(step):
    world.browser.find_by_css('.login a').first.click()
    world.wait_for_element_by_css('.login_submit a')
    world.browser.find_by_css('.login_submit a').first.click()

@step('(?:Given|And) there is a username "([^"]*)" with password "([^"]*)"')
def make_user(step, username, password):
    if username in ['test', 'subject']:
        # Should already have been created in the test-fixture
        # fixture file; so no need to create it here.
        return
    user = User.objects.create_user(username,
      '%s@example.com' % username, password)
    user.save()

@step(r'When I fill in my username "([^"]*)" and my password "([^"]*)"')
def fill_in(step, username, password):
    world.browser.find_by_css('div.login input[name=user_or_email]').first.fill(username)
    world.browser.find_by_css('div.login input[name=password]').first.fill(password)

@step(r'''And I click the page's "([^"]*)" button''')
def click_button(step, button):
    world.browser.find_by_css('.login').first.find_by_value(button).first.click()

@step('Then user "([^"]*)" is logged in')
def logged_in(step, username):
    assert world.browser.find_link_by_text(username)

@step(u'Given user "([^"]*)" with password "([^"]*)" is logged in')
def create_and_login(step, username, password):
    step.behave_as("""
    Given there is a username "%(username)s" with password "%(password)s"
    """ % locals())
    world.browser.visit(django_url('/docs/'))
    l = world.FakeLogin()
    cookie_data = l.login(username, password) 
    world.browser.driver.add_cookie(cookie_data)

@step(u'(?:Given|And) I am not logged in')
def given_i_am_not_logged_in(step):
    world.browser.driver.delete_all_cookies()

@step(u'(?:Then|And) I should be on my profile page')
def and_i_should_be_on_my_profile_page(step):
    assert '/profiles/' in world.browser.url

