from nose.tools import assert_equals, raises
import sys
import urllib
import re
import datetime

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives

from frontend.models import UserProfile
from codewiki.models import Vault, Invite, Scraper, ScraperRunEvent
from frontend.views import vault_users, invite_to_vault, login

import helper
from mock import Mock, patch

def setup():
    global profile
    global user
    username,password = 'testing','pass'
    user = User.objects.create_user(username, '%s@example.com' % username, password)
    profile = user.get_profile()

@raises(PermissionDenied)
def ensure_freeloaders_cannot_create_vault():
    profile.change_plan('free')
    profile.create_vault(name='avault')

def ensure_paying_user_can_create_vault():
    for plan in ('individual', 'business', 'corporate'):
        yield user_plan_create_vault, plan

def ensure_vault_is_saved():
    profile.change_plan('individual')
    vault = profile.create_vault(name='avault')
    id = vault.id
    db_vault = Vault.objects.filter(id=id)[0]
    assert_equals(db_vault.user, user)

def user_plan_create_vault(plan):
    profile.change_plan(plan)
    vault = profile.create_vault(name='avault')
    assert_equals(vault.user, user)
    
@patch('frontend.views.invite_to_vault')
def ensure_vault_owner_can_invite_new_member_by_email(mock_invite):
    mock_invite.return_value = 'ok'
    profile.change_plan('corporate')
    vault = profile.create_vault(name='invitevault')
    email = 'newuser@example.com'
    factory = helper.RequestFactory()
    url = '/vaults/%s/adduser/%s/' % (vault.id, urllib.quote(email))
    request = factory.get(url, 
      dict(HTTP_X_REQUESTED_WITH='XMLHttpRequest'))
    request.user = user
    response = vault_users(request, vault.id, email, 'adduser')
    assert mock_invite.called

@patch.object(EmailMultiAlternatives, 'send')
def ensure_invite_new_member_sends_email(mock_send):
    vault = profile.create_vault(name='invitevault')
    email = 'testing@example.com'
    response = invite_to_vault(user, email, vault)
    assert mock_send.called

@patch.object(EmailMultiAlternatives, 'attach_alternative')
def ensure_invitation_email_contains_invite_token(mock_email):
    vault = profile.create_vault(name='invitevault')
    email = 'testing@example.com'
    response = invite_to_vault(user, email, vault)
    assert re.search("/login/\?t=[a-fA-F0-9]{20}",
                        repr(mock_email.call_args_list))

@patch.object(EmailMultiAlternatives, 'attach_alternative')
def it_should_save_an_invite_token_and_vault_id_and_email_address(mock_email):
    vault = profile.create_vault(name='invitevault')
    email = 'test@example.com'
    response = invite_to_vault(user, email, vault)

    token = re.search("/login/\?t=([a-fA-F0-9]{20})",
                        repr(mock_email.call_args_list)).group(1)
    invite = Invite.objects.get(token=token)
    assert invite
    assert_equals(invite.vault.id, vault.id)
    assert_equals(invite.email, email)

@patch.object(EmailMultiAlternatives, 'attach_alternative')
def it_should_add_the_user_to_the_vault_on_sign_up(mock_email):
    vault = profile.create_vault(name='invitevault')
    email = 'testier@closedblueprints.com'
    response = invite_to_vault(user, email, vault)

    token = re.search("/login/\?t=([a-fA-F0-9]{20})",
                        repr(mock_email.call_args_list)).group(1)

    factory = helper.RequestFactory()
    params = {'name': 'Testier Monsenur',
              'username': 'testier',
              'email': 'testier@closedblueprints.com',
              'password1': 'pass',
              'password2': 'pass',
              'tos': 'checked',
              'token': token,
              'register': 'yes',
             }
    request = factory.post('/login/', params)

    response = login(request)
    
    testier = User.objects.get(username='testier')
    assert testier
    assert testier in vault.members.all()

# test that token is required
