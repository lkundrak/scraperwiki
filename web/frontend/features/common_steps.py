import time

import splinter
from lettuce import step,before,world,after
from lettuce.django import django_url
from django.contrib.auth.models import User
from frontend.models import UserProfile, Feature
from nose.tools import assert_equals

# Steps used in more than one feature's steps file

# Human readable CSS selectors
SELECTORS = {
        'need help box':                "div[@id='help']",
        }

# Features
@step(u'(?:Given|And) the "([^"]*)" feature exists')
def and_the_feature_exists(step, feature):
    Feature.objects.filter(name=feature).delete()
    Feature.objects.create(name=feature, public=True)

@step(u'(?:Given|And) I have the "([^"]*)" feature enabled')
def and_i_have_a_feature_enabled(step, feature):
    u = User.objects.filter(username='test')[0]
    feature = Feature.objects.filter(name=feature)[0]
    profile = u.get_profile();
    profile.features.add(feature)
    assert profile.has_feature(feature)

@step(u'And I do not have the "([^"]*)" feature enabled$')
def feature_not_enabled(step, feature):
    u = User.objects.filter(username='test')[0]
    feature = Feature.objects.filter(name=feature)[0]
    profile = u.get_profile();

    try:
        profile.features.remove(feature)
    except ValueError:
        # Expected when the user already does not have the
        # feature in question.
        pass

    assert not profile.has_feature(feature)


# Payment plan
@step(u'(?:Given|And) I am an? "([^"]*)" user') 
def given_i_am_a_plan_user(step, plan):
    plan = plan.replace(' ', '').lower()
    step.behave_as("""
    Given user "test" with password "pass" is logged in
    And I am on the "%s" plan
    """ % plan)

@step(u'And I am on the "([^"]*)" plan')
def and_i_am_on_the_plan(step, plan):
    user = User.objects.get(username='test')
    profile = user.get_profile()
    profile.change_plan(plan)

# Scrapers
@step(u"(?:When|And) I visit my scraper's overview page$")
def i_am_on_the_scraper_overview_page(step):
    world.browser.visit(django_url('/scrapers/test_scraper'))

# Seeing matchers

@step(u'(?:Then|And) I should (not )?see "([^"]*)"')
def and_i_should_not_see_text(step, negative, text):
    x = world.browser.is_text_present(text)
    if not negative:
        assert x
    else:
        assert not x

@step(u'(?:Then|And) I should (not )?see (?:the|a|an) "([^"]*)" (?:link|button)$')
def i_should_see_the_button(step, negative, text):
    x = world.browser.find_link_by_partial_text(text)
    if not negative:
        assert x
    else:
        assert x == []

@step(u'(?:Then|And) I should see (?:the|a|an) "([^"]*)" (?:link|button) in the (.+)')
def i_should_see_the_button_in_parent(step, text, parent_name):
    xpath = ".//%s//a[contains(.,'%s')]" % (
      SELECTORS[parent_name], text)
    assert world.browser.find_by_xpath(xpath)

# Clicking
@step(u'(?:And|When) I click "([^"]*)"')
def and_i_click(step, text):
    # :todo: Make it not wrong.  so wrong.
    world.browser.find_by_tag("button").first.click()

@step(u'(?:When|And) I click the "([^"]*)" (?:link|button)$')
def i_click_the_button(step, text):
    try:
        world.browser.find_link_by_partial_text(text).first.click()
    except splinter.exceptions.ElementDoesNotExist:
        # Sometimes we have an actual button, in which case we end up here.
        world.browser.find_by_value(text).first.click()

# Alerts
@step(u'(?:Then|And) I close the alert')
def and_i_close_the_alert(step):
    world.browser.find_by_css('#alert_close').first.click()

