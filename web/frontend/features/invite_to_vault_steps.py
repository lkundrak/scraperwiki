import sys
import re
import time

import splinter
from lettuce import step,before,world,after
from lettuce.django import django_url
from django.core import mail

@step(u'(?:When|And) I click the vault members button')
def i_click_the_vault_members_button(step):
    world.browser.find_by_css('div.vault').first.find_by_css('a.vault_users').first.click()
    world.wait_for_fx()

@step(u'(?:Then|And) I type "([^"]*)" into the username box$')
def i_type_into_the_username_box(step, text):
    world.browser.find_by_css('div.vault').first.find_by_css('input.username').first.fill(text)
    # Bit hacky, we may need to wait for the button to be truly visible.
    world.wait_for_element_by_css('.new_user a')

@step(u'Then an invitation email gets sent to "([^"]*)"')
def then_an_invitation_email_gets_sent_to(step, address):
    # Could check RE here, something like ("To:.*%s" % address).
    time.sleep(0.5) # need to wait a little bit for the mail, refactor!
    assert world.mails_len() == 1, world.mails_file()
    assert address in world.mails_body()[0]

@step(u'Given I have been invited to scraperwiki')
def given_i_have_been_invited_to_scraperwiki(step):
    step.behave_as(
        """
        Given I am a "Corporate" user
        And I have a vault
        And I am on the vaults page
        When I click the vault members button
        And I click the "Add another user" button
        And I type "t.test@testersonandsons.com" into the username box
        And I click the "Add!" button
        """)

@step(u'And there is a sign up link in the invitation email')
def and_there_is_a_sign_up_link_in_the_invitation_email(step):
    time.sleep(0.5)
    assert "/login/?t=" in world.mails_body()[0]

@step(u'When I go to the invitation link in the email')
def when_i_go_to_the_invitation_link_in_the_email(step):
    # "3D" is quoted printable nastiness.
    # The '.*' and re.DOTALL conspire to mean that we find the
    # last occurence of a token, which is the one we want when
    # there are many email messages in the file.
    token = re.search(".*/login/\?t=3D([a-fA-F0-9]{20})",
                world.mails_body()[0], re.DOTALL).group(1)
    world.browser.visit(django_url('/login/?t=%s' % token))

@step(u'And I should see the vault name')
def and_i_should_see_the_vault_name(step):
    step.behave_as("""
        Then I should see "My #1 Vault"
        """)

@step(u'And I should see my email already filled in')
def and_i_should_see_my_email_already_filled_in(step):
    email = "t.test@testersonandsons.com"
    assert email in world.browser.find_by_css('#id_email').first.value


@step(u'When I sign up')
def when_i_sign_up(step):
    world.browser.visit(django_url('/login/'))

    world.browser.find_by_css('#id_name').first.fill('Lord Test Testerson')
    world.browser.find_by_css('#id_email').first.fill('t.test@testersonandsons.com')
    world.browser.find_by_css('#id_password1').first.fill('pass')
    world.browser.find_by_css('#id_password2').first.fill('pass')
    world.browser.find_by_css('#id_tos').first.check()
    world.browser.find_by_value("Create my account").first.click()

@step(u'When I mess my sign up')
def mess_sign_up(step):
    step.behave_as("""
        And there is a sign up link in the invitation email
        When I go to the invitation link in the email
        Then I should be on the sign up page
        """)
    # Clicking without filling anything else in should be enough
    # to provoke an invalid form.
    step.behave_as("""
        And I click the "Create my account" button
        """)

@step(u'And I should have access to the vault I was invited to')
def and_i_should_have_a_vault(step):
    step.behave_as("""
                   When I visit the vaults page
                   Then I should see "My #1 Vault"
                   """)

@step("And the vault owner has been emailed")
def vault_owner_emailed(step):
    time.sleep(0.5)
    m = re.search(r"^To:\s+test@example.com",
      world.mails_body()[-1],
      re.M)
    assert m, world.mails_file()

