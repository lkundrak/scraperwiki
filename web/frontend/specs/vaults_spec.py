from nose.tools import assert_equals, raises

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from frontend.models import UserProfile
from codewiki.models import Vault

def setup():
    global profile
    global user
    username,password = 'test','pass'
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
    
