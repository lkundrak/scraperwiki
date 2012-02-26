from django.template import Library
from django.conf import settings

register = Library()

@register.inclusion_tag('codewiki/templatetags/history.html')
def history(scraper, user, count=-1):
    from codewiki.views import populate_itemlog
    itemlog = populate_itemlog( scraper, count)
    return {
        'scraper': scraper,
        'itemlog': itemlog,
        'user': user
    }

