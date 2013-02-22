from nose.tools import assert_equals, raises
import sys
import urllib
import re
import datetime

from django.core.management import call_command
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives

import helper
from mock import Mock, patch

from codewiki.models import Vault, Scraper, ScraperRunEvent
from alerts.views import (
    alert_vault_members_of_exceptions,
    select_exceptions_that_have_not_been_notified,
    compose_email
    )


def setUp():
    global profile
    global user
    global scraper
    global vault
    global runevent
    username,password = 'testing','pass'
    user = User.objects.create_user(username, '%s@example.com' % username, password)
    profile = user.get_profile()
    profile.plan = 'business'

def tearDown():
    vault.delete()
    scraper.delete()
    user.delete()

def ensure_django_management_command_works():
    global vault, scraper, runevent
    _make_vault_with_runevent('yes_exceptions_vault', 'FakeError: This is a test.')
    call_command('notify_vault_exceptions')

    print('Not notified count: %d' % ScraperRunEvent.objects.filter(notified = True).count())
    assert ScraperRunEvent.objects.filter(notified = True).count() == 1


@patch.object(EmailMultiAlternatives, 'send')
def ensure_exceptionless_vault_has_not_been_notified(mock_send):
    _make_vault_with_runevent('no_exceptions_vault', '')
    response = alert_vault_members_of_exceptions(vault)

    query_runevent_again = ScraperRunEvent.objects.filter(pk = runevent.pk)[0]
    assert query_runevent_again.notified == False

@patch.object(EmailMultiAlternatives, 'send')
def ensure_exceptional_vault_has_been_notified(mock_send):
    global vault, scraper, runevent
    _make_vault_with_runevent('yes_exceptions_vault', 'FakeError: This is a test.')
    response = alert_vault_members_of_exceptions(vault)

    query_runevent_again = ScraperRunEvent.objects.filter(pk = runevent.pk)[0]
    assert query_runevent_again.notified == True

@patch.object(EmailMultiAlternatives, 'send')
def ensure_exceptionless_vault_receives_no_email(mock_send):
    _make_vault_with_runevent('no_exceptions_vault', '')
    response = alert_vault_members_of_exceptions(vault)
    assert not mock_send.called

@patch.object(EmailMultiAlternatives, 'send')
def ensure_exceptional_vault_receives_email(mock_send):
    _make_vault_with_runevent('yes_exceptions_vault', 'FakeError: This is a test.')
    response = alert_vault_members_of_exceptions(vault)
    assert mock_send.called

def _ensure_emails_contains_scraper_name(i):
    _make_vault_with_runevent('yes_exceptions_vault', 'FakeError: This is a test.')
    runevents = select_exceptions_that_have_not_been_notified(vault)
    assert "Bucket-Wheel Excavators" in compose_email(runevents, vault)[i]

def ensure_text_email_contains_scraper_name():
    _ensure_emails_contains_scraper_name('text')

def ensure_html_email_contains_scraper_name():
    _ensure_emails_contains_scraper_name('html')

def _make_vault_with_runevent(name, exception_message):
    global vault, scraper, runevent
    vault = profile.create_vault(name=name)
    scraper = Scraper.objects.create(
        title=u"Bucket-Wheel Excavators", vault = vault,
    )
    runevent = ScraperRunEvent.objects.create(
        scraper=scraper, pid=-1,
        exception_message=exception_message,
        run_started=datetime.datetime.now()
    )
