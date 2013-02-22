from lettuce import step,before,world
from django.contrib.auth.models import User
from lettuce.django import django_url

@step(u'When I sign up')
def when_i_sign_up(step):
    world.browser.visit(django_url('/login/'))

    world.browser.find_by_css('#id_name').first.fill('Lord Test Testerson')
    world.browser.find_by_css('#id_email').first.fill('t.test@testersonandsons.com')
    world.browser.find_by_css('#id_password1').first.fill('pass')
    world.browser.find_by_css('#id_password2').first.fill('pass')
    world.browser.find_by_css('#id_tos').first.check()
    world.browser.find_by_value("Create my account").first.click()
    
@step(u'(?:Then|And) I should be on my profile page')
def and_i_should_be_on_my_profile_page(step):
    assert '/profiles/' in world.browser.url