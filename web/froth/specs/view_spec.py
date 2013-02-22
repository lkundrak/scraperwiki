import json

from django.contrib.auth.models import User
from django.conf import settings
import helper

from froth.views import check_key

def setUp():    
    global user, profile
    user = User.objects.create_user('dcameron', 'dcameron@scraperwiki.com', 'bagger288')
    profile = user.get_profile()

def ensure_staff_key_returns_valid_response():
    user.is_staff = True
    user.save()

    rf = helper.RequestFactory()
    mock_request = rf.get('/froth/check_key')
    response = check_key(mock_request, profile.apikey)
    assert response.status_code == 200

    user.is_staff = False
    user.save()

def ensure_valid_key_returns_org():
    # We understand that the org returned by froth is the scraperwiki.com
    # username.
    profile.plan = 'business'
    profile.save()
    rf = helper.RequestFactory()
    mock_request = rf.get('/froth/check_key')
    response = check_key(mock_request, profile.apikey)
    assert response.status_code == 200
    profile.plan = 'free'
    profile.save()
    j = json.loads(response.content)
    assert 'org' in j
    assert j['org'] == user.username

def ensure_premium_account_holder_key_returns_valid_response():
    for plan in ('individual', 'business', 'corporate'):
        profile.plan = plan
        profile.save()
        rf = helper.RequestFactory()
        mock_request = rf.get('/froth/check_key')
        response = check_key(mock_request, profile.apikey)
        assert response.status_code == 200
    profile.plan = 'free'
    profile.save()

def ensure_invalid_key_returns_invalid_response():
    rf = helper.RequestFactory()
    mock_request = rf.get('/froth/check_key')
    response = check_key(mock_request, "There's no way this is a valid api key.")
    assert response.status_code == 403 # Forbidden

def ensure_peasant_key_returns_invalid_response():
    """Users who are not staff and not holders of premium accounts
    should not have valid API keys."""

    # We don't actually need the next four lines.
    profile.plan = 'free'
    profile.save()
    user.is_staff = False
    user.save()

    rf = helper.RequestFactory()
    mock_request = rf.get('/froth/check_key')
    response = check_key(mock_request, profile.apikey)
    assert response.status_code == 402 # PaymentRequired
