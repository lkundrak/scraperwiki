from django.test import TestCase

from codewiki.models import Scraper
from django.contrib.auth.models import User

class Test__unicode__(TestCase):
    def test_scraper_name(self):
        self.assertEqual(
            'test_scraper',
            unicode(Scraper(title='Test Scraper', short_name='test_scraper'))
        )