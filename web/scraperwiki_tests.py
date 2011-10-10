from django.test.simple import run_tests as default_run_tests 
from django.conf import settings 

def run_tests(test_labels, *args, **kwargs): 
    # default to all ScraperWiki apps (so we don't run all the Django app tests etc.)
    if len(test_labels) == 0:
        test_labels = settings.SCRAPERWIKI_APPS

    return default_run_tests(test_labels, *args, **kwargs) 
