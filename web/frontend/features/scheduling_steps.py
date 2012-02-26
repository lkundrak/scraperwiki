from lettuce.django import django_url
from lettuce import step,before,world,after
from django.contrib.auth.models import User
from frontend.models import Feature
from codewiki.models import Scraper
import re
import time

@before.each_scenario
def reset_schedule(scenario):
    scraper = Scraper.objects.get(pk=1)    
    scraper.run_interval = -1
    scraper.save()
    
@step(u'Then I should see the scheduling panel')
def then_i_should_see_the_scheduling_panel(step):
    assert world.browser.find_by_css(".schedule")
    
@step(u'And I should see the button to edit the schedule')
def and_i_should_see_the_button(step):
    assert world.browser.find_by_css("a.edit_schedule")
    
@step(u"(?:When|And) I visit my scraper's overview page$")
def and_i_am_on_the_scraper_overview_page(step):
    world.browser.visit(django_url('/scrapers/test_scraper'))

@step(u'When I click the "([^"]*)" button in the scheduling panel')
def when_i_click_a_button_in_the_scheduling_panel(step, button):
    panel = world.browser.find_by_css("td.schedule").first
    panel.find_by_css("a." + button.lower()).first.click()
    world.wait_for_fx()
    
@step(u'Then I should see the following scheduling options:')
def then_i_should_see_the_scheduling_options(step):
    for label in step.hashes:
        xpath = ".//table[@id='edit_schedule']//label[text()=\"%s\"]" % label["Don't schedule"]
        assert world.browser.find_by_xpath(xpath)

@step(u'And I click the "([^"]*)" schedule option')
def when_i_click_the_schedule_option(step, option):
    xpath = ".//table[@id='edit_schedule']//label[text()=\"%s\"]" % option
    world.browser.find_by_xpath(xpath).first.click()
    world.wait_for_ajax()

@step(u'Then the scraper should be set to "([^"]*)"')
def then_the_scraper_should_be_set_to_schedule(step, schedule):
    step.behave_as('Then I should see "%s"' % schedule)