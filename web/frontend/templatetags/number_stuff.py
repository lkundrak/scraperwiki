from django.template import Library
from django.contrib.humanize.templatetags.humanize import intcomma
import calendar

register = Library()

def plusminus_int(number):
    try:
        num = int(number)
        if num >= 0:
            return "+" + intcomma(str(num))
        else:
            return intcomma(str(num))
    except:
        return ""

register.filter('plusminus_int', plusminus_int)
