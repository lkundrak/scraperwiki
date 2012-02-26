from lettuce import step,before,world,after
from lettuce.django import django_url

@step(u'(?:When|And) I choose to write my scraper in "([^"]*)"')
def when_i_choose_to_write_my_scraper_in(step, language):
    world.browser.find_link_by_href("/scrapers/new/%s" % language.lower()).first.click()
    
@step(u'And I create a scraper')
def and_i_create_a_scraper(step):
    step.behave_as("""
        And I am on the home page
        And I click the "Create a scraper" button
        And I choose to write my scraper in "Python"
        Then I should be on the python scraper code editing page
    """
    )

@step(u'When I save the scraper as "([^"]*)"')
def when_i_save_the_scraper_as(step, name):
    world.browser.find_by_value("save scraper").first.click()
    # See http://splinter.cobrateam.info/docs/iframes-and-alerts.html
    prompt = world.browser.get_alert()
    prompt.fill_with(name)
    prompt.accept()

@step(u'Then I should be on my "([^"]*)" scraper page')
def then_i_should_be_on_my_scraper_page(step, scraper_name):
    url = '/scrapers/%s/edit/' % scraper_name.lower()
    world.wait_for_url(django_url(url))
    assert url in world.browser.url
                                
