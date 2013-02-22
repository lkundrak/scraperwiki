from nose.tools import assert_equals, raises

from frontend.models import UserProfile
from django.contrib.auth.models import User

def setup():
    global user
    username,password = 'tester','pass'
    user = User.objects.create_user(username, '%s@example.com' % username, password)

def ensure_can_upgrade_account():
    profile = user.get_profile()
    profile.change_plan('individual')
    assert_equals(profile.plan, 'individual')
    profile.change_plan('business')
    assert_equals(profile.plan, 'business')
    profile.change_plan('corporate')
    assert_equals(profile.plan, 'corporate')
    profile.change_plan('free')
    assert_equals(profile.plan, 'free')

def ensure_account_upgraded():
    profile = user.get_profile()
    profile.change_plan('corporate')
    db_user = User.objects.filter(username=user.username)[0]
    profile = db_user.get_profile()
    
    assert_equals(profile.plan, 'corporate')

@raises(ValueError)
def it_should_not_allow_an_invalid_plan():
    profile = user.get_profile()
    profile.change_plan('h0h0h0')
