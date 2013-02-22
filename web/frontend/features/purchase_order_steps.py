from lettuce import step,before,world

@step(u'Then I should see a message about paying with a purchase order')
def then_i_should_see_a_message_about_paying_with_a_purchase_order(step):
    assert world.browser.is_text_present('purchase order')

@step(u'And the subject type "([^"]*)" should be selected')
def and_the_subject_type_should_be_selected(step, subject):
    assert world.browser.find_by_xpath('.//option[text()="%s"]' % subject).first.selected

