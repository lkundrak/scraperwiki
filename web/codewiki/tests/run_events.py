from django.test import TestCase
from datetime import datetime

from codewiki.models import Scraper, ScraperRunEvent

class TestRunEvents(TestCase):
    def setUp(self):
        self.scraper = Scraper.objects.create(title=u"Scraper 1")

    def testMe(self):
        sre = ScraperRunEvent.objects.create(scraper=self.scraper, run_id='XXX', pid=666, run_started=datetime.now())
