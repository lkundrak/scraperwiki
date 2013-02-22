from lettuce import step,before,world,after
from lettuce.django import django_url
from django.contrib.auth.models import User
from frontend.models import Feature
from codewiki.models import Scraper

@before.each_scenario
def reset_schedule(scenario):
    scraper = Scraper.objects.get(pk=1)    
    scraper.run_interval = -1
    scraper.save()
    
@step(u'Given I am an? "([^"]*)" user')
def given_i_am_a_plan_user(step, plan):
    plan = plan.replace(' ', '').lower()
    step.behave_as("""
    Given user "test" with password "pass" is logged in
    And I am on the "%s" plan
    """ % plan)

@step(u'(?:Then|And) I should see the privacy panel')
def i_should_see_the_privacy_panel(step):
    assert world.browser.find_by_css("#privacy_status")

@step(u'(?:Then|And) I should see the button to change the privacy settings')
def i_should_see_the_button_to_change_the_privacy_settings(step):
    assert world.browser.find_by_css("#show_privacy_choices")

@step(u'(?:When|And) I click the privacy button')
def i_click_the_privacy_button(step):
    world.browser.find_by_css("#collaboration .buttons li a").first.click()

@step(u'(?:When|And) I click the change privacy button')
def i_click_the_change_privacy_button(step):
    world.browser.find_by_css("#show_privacy_choices").first.click()

@step(u"(?:When|And) I visit my scraper's overview page$")
def and_i_am_on_the_scraper_overview_page(step):
    world.browser.visit(django_url('/scrapers/test_scraper'))

@step(u'(?:Given|And) I am on the "([^"]*)" plan')
def i_am_on_the_plan(step, plan):
    user = User.objects.get(username='test')
    profile = user.get_profile()
    profile.change_plan(plan)
