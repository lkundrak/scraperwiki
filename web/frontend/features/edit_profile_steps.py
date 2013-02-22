from lettuce import step,before,world,after

@step(u'Then I should see the API key')
def then_i_should_see_the_api_key(step):
    apikey =  "5b7e6c1b-cfab-4485-bda0-8b00bdd7b2ea"
    element =  world.browser.find_by_css("#apikey")
    assert element
    assert apikey in element.first.text

@step(u'Then I should not see the API key')
def then_i_should_not_see_the_api_key(step):
    assert not world.browser.find_by_css("#apikey")

