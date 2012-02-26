from django.template import Library
from django.template.defaultfilters import stringfilter
from django.conf import settings

import re
register = Library()

@register.inclusion_tag('codewiki/templatetags/screenshot.html')
def screen_shot(code_object, size='medium'):
    
    has_screenshot = code_object.has_screenshot(size=size)
    url = code_object.screenshot_url(size=size)
    
    return {
        'url': url,
        'has_screenshot': has_screenshot,        
        'title': code_object.title,    
    }


