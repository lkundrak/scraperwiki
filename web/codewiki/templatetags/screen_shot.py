from django.template import Library
from django.template.defaultfilters import stringfilter
from django.conf import settings

import re
register = Library()

@register.inclusion_tag('codewiki/templatetags/screenshot.html')
def screen_shot(code_object, size='medium'):
    
    has_screenshot = code_object.has_screenshot(size=size)
    if has_screenshot:
        url = settings.MEDIA_URL + 'screenshots/' + size + '/' + code_object.get_screenshot_filename(size=size)
    else:
        url = settings.MEDIA_URL + 'images/testcard_' + size + '.png'
        
    return {
        'url': url,
        'has_screenshot': has_screenshot,        
        'title': code_object.title,    
    }

