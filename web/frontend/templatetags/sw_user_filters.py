from django.template import Library

register = Library()

def num_scrapers(user):
    return user.code_set.filter(wiki_type='scraper').distinct().count()

def num_views(user):
    return user.code_set.filter(wiki_type='view').distinct().count()

register.filter('num_scrapers', num_scrapers)
register.filter('num_views', num_views)
