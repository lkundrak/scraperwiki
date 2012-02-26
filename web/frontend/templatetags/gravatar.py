import urllib, hashlib
import os
from django import template
from django.http import HttpResponse
from django.conf import settings
from django.contrib.sites.models import Site

register = template.Library()

@register.inclusion_tag('frontend/templatetags/gravatar.html')

def show_gravatar(user, size = 'medium'):

    #work out size
    size_px = 0
    if size == 'small':
        size_px = 20
    elif size == 'medium':
        size_px = 40
    elif size == 'large':
        size_px = 125

    domain = Site.objects.get_current().domain
    defaultimg =  settings.MEDIA_URL + "images/gravatar_default.png"
    gravatar_id = user and hashlib.md5(user.email).hexdigest() or ''
    gravatardata = urllib.urlencode({'gravatar_id': gravatar_id, 'size': str(size_px), 'd': 'identicon'})
    
    url = "https://secure.gravatar.com/avatar.php?%s" % gravatardata
    username = user and user.username or ''
    return {'gravatar': {'url':url, 'size':size, 'size_px':size_px, 'username':username }}
