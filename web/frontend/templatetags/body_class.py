#!/usr/bin/env python

from django import template
from django.utils.html import escape

register = template.Library()

@register.simple_tag
def body_class(request):
    if request.path == '/':
        return 'frontpage'
    else:
        classes = ' '.join(request.path[1:].split('/')).strip()
        return escape(classes)
