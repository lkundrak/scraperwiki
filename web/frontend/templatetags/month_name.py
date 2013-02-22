from django.template import Library
import calendar

register = Library()

def month_name(number):
    try:
        num = int(number)
        return calendar.month_name[num]
    except:
        return ""

register.filter('month_name', month_name)
