from nose.tools import assert_equals, raises
import datetime

from django.conf import settings
from django.contrib.auth.models import User

from codewiki.models.scraper import Scraper, ScraperRunEvent
from codewiki.models.vault import Vault
from alerts.views import select_exceptions_that_have_not_been_notified

today = datetime.datetime.now()

def setUp():
    global user
    global scraper
    global vault
    global profile
    user = User.objects.create_user('dcameron', 'dcameron@scraperwiki.com', 'bagger288')
    profile = user.get_profile()
    profile.plan = 'business'
    vault = Vault.objects.create(user = user)
    scraper1 = Scraper.objects.create(
        title=u"Lucky Scraper 1", vault = vault,
    )
    scraper2 = Scraper.objects.create(
        title=u"Lucky Scraper 2", vault = vault,
    )

    yesterday = today - datetime.timedelta(days=1)

    runevent1a = ScraperRunEvent.objects.create(
        scraper=scraper1, pid=-1,
        exception_message=u'FakeError: This is a test.',
        run_started=yesterday
    )
    runevent1b = ScraperRunEvent.objects.create(
        scraper=scraper1, pid=-1,
        exception_message='',
        run_started=today
    )

    runevent2a = ScraperRunEvent.objects.create(
        scraper=scraper2, pid=-1,
        exception_message='',
        run_started=yesterday
    )
    runevent2b = ScraperRunEvent.objects.create(
        scraper=scraper2, pid=-1,
        exception_message=u'FakeError: This is a test.',
        run_started=today
    )
    runevent2c = ScraperRunEvent.objects.create(
        scraper=scraper2, pid=-1,
        exception_message=u'FakeError: This is a test.',
        run_started=today
    )

def ensure_find_exceptional_scrapers_in_vault():
    observed_count = len(select_exceptions_that_have_not_been_notified(vault))
    expected_count = 1
    assert observed_count == expected_count

def test_runevents_have_notified_flag():
    """A runevent should have a notified flag."""

    scraper = Scraper.objects.filter(id=1)[0]
    event = ScraperRunEvent.objects.create(scraper=scraper, pid=-1,
      run_started=today)

    # This will raise an error if event doesn't have a notified column
    assert event.notified == False

def ensure_notified_runevents_are_not_selected():
    local_vault = profile.create_vault(name='Magnifying glasses')
    local_scraper = Scraper.objects.create(
        title=u"Bucket-Wheel Excavators", vault = local_vault,
    )
    local_runevent = ScraperRunEvent.objects.create(
        scraper=local_scraper, pid=-1,
        exception_message='saoenstueaonsueaonsueao',
        run_started=datetime.datetime.now(),
        notified=True
    )

    assert [] == select_exceptions_that_have_not_been_notified(local_vault)

def ensure_only_most_recent_runevent_is_selected():
    local_vault = profile.create_vault(name='Magnifying glasses')
    local_scraper = Scraper.objects.create(
        title=u"Bucket-Wheel Excavators", vault = local_vault,
    )
    local_runevent = ScraperRunEvent.objects.create(
        scraper=local_scraper, pid=-1,
        exception_message='saoenstueaonsueaonsueao',
        run_started=datetime.datetime.now()-datetime.timedelta(minutes=3),
        notified=False
    )
    local_runevent = ScraperRunEvent.objects.create(
        scraper=local_scraper, pid=-1,
        exception_message='saoenstueaonsueaonsueao',
        run_started=datetime.datetime.now()-datetime.timedelta(minutes=1),
        notified=False
    )
    local_runevent = ScraperRunEvent.objects.create(
        scraper=local_scraper, pid=-1,
        exception_message='saoenstueaonsueaonsueao',
        run_started=datetime.datetime.now(),
        notified=True
    )

    assert [] == select_exceptions_that_have_not_been_notified(local_vault)
