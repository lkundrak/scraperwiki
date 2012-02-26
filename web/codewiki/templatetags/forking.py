from django.template import Library
from django.conf import settings

register = Library()

@register.inclusion_tag('codewiki/templatetags/forked_to.html')
def forked_to(scraper, count=5):
    from codewiki.models import Scraper
    scrapers = Scraper.objects.filter(forked_from=scraper).exclude(privacy_status='deleted').exclude(privacy_status='private').order_by('-created_at')[0:5]
    return {
        'forks': scrapers,
    }

