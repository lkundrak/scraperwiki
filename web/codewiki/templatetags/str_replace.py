from django.template import Library
from django.template.defaultfilters import stringfilter

import re
register = Library()

@register.simple_tag
def str_replace(search, replace, subject):
    return re.sub(search,replace,subject)
