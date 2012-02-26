from lettuce import step,before,world
from django.contrib.auth.models import User
from frontend.models import UserProfile, Feature
from nose.tools import assert_equals,assert_less
import time

prefix = 'http://localhost:8000'
service_xpath = "//h3[a[contains(strong,'%s')]]"

@step(u'When I visit the request page')
def when_i_visit_the_request_page(step):
    response = world.browser.visit(prefix + '/request_data/')


@step(u'When I visit the public request page')
def when_i_visit_the_public_request_page(step):
    response = world.browser.visit(prefix + '/request_data/public/')



@step(u'And I click on "([^"]*)"')
def and_i_click_on_group1(step, text):
    el = world.browser.find_by_xpath("//a[text()='%s']" % text).first
    el.click()

@step(u'Then I should be on the request page')
def then_i_should_be_on_the_request_page(step):
    assert '/request_data' in world.browser.url

@step(u'Then I should be on the public request page')
def then_i_should_be_on_the_public_request_page(step):
    assert '/request_data/public' in world.browser.url

@step(u'And I click the "([^"]*)" services button')
def and_i_click_the_group1_services_button(step, service):
    el = world.browser.find_by_xpath((service_xpath % service)+'/a').first
    el.click()

@step(u'(?:Then|And) I should see the "([^"]*)" service')
def then_i_should_see_the_services(step, plan):
    plans = world.browser.find_by_xpath(service_xpath % plan)
    assert_equals(1, len(plans))

@step(u'(?:Then|And) I should see a link to "([^"]*)"')
def then_i_should_see_a_link(step, url):
    nodes = world.browser.find_by_xpath("//a[@href='%s']" % url)
    assert_less(0, len(nodes))

@step(u'(?:And|Then) I should see "([^"]*)"$')
def then_i_should_see(step, text):
    assert world.browser.is_text_present(text)
