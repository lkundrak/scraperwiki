from lettuce import step,before,world,after
from lettuce.django import django_url

@step("And I am on my profile page")
def profile_page(step):
    step.behave_as("""
        And I am on the contact page
        """)
    # find URL to profile page
    el = world.browser.find_by_xpath(
      "//a[contains(@href, '/profiles/')]").first
    world.browser.visit(el['href'])

@step('Then I should be on my edit profile page')
def edit_profile_page(step):
    assert 'profile' in world.browser.url
    assert 'edit' in world.browser.url

@step('Given I am a user with no scrapers')
def user_no_scrapers(step):
    # Not logged in.
    world.browser.visit(django_url('/profiles/subject/'))
    assert world.browser.is_text_present('no scrapers')
    # As of 2012-04-16 user 'subject' has no scrapers.
    step.behave_as("""
    Given user "subject" with password "pass" is logged in
    """)
    
