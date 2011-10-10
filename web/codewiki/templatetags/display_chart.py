from django import template
from django.utils.safestring import mark_safe
try:
    import json
except:
    import simplejson as json

register = template.Library()

def display_chart(value):
    try:
        # This is nasty, but it's more secure than using eval
        d = json.loads(value.replace("'", '"'))
        chartimg = d.get('chartimg')
        
        if chartimg.startswith('http://chart.apis.google.com/chart?'):
            img = "<img src=\"%s\"/>" % chartimg
            return mark_safe(img)
        else:
            return value
    except Exception, ex:
        return value

register.filter('display_chart', display_chart)
