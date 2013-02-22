from lettuce import step,before,world,after
from lettuce.django import django_url

from codewiki.models import Scraper

@step(u'When I enter "([^"]*)" in the search box')
def when_i_fill_in_the_search_box_with_text(step, text):
    element = world.browser.find_by_css('.search input.text')
    element.fill(text)
    element.type('\n')

@step(u'Given the "([^"]*)" has the tag "([^"]*)"')
def given_a_the_scraper_has_the_tag(step, scraper, tag):
    scraper = Scraper.objects.get(short_name=scraper)
    scraper.settags(tag)
