import unittest
import datetime
from codewiki.models import Scraper
from codewiki.util import get_overdue_scrapers

class TestRunScrapers(unittest.TestCase):
    def setUp(self):
        # Remove any Scrapers created by a fixture
        [x.delete() for x in Scraper.objects.all()]
        self.scrapers = get_overdue_scrapers()

    def testNeverRun(self):
        # Published scrapers that have never been run should
        # appear in the list of scrapers to be run
        never_run = Scraper(title=u'Never Run',
                            last_run=None,
                            run_interval=86400)
        never_run.save()
        self.assertEqual(1, self.scrapers.count())

    def testNotOverdue(self):
        # Scrapers that haven't been run for less than the run interval
        # should not appear in the list of scrapers to be run
        not_overdue = Scraper(title=u'Not Overdue',
                              last_run=datetime.datetime.now(), 
                              run_interval=86400)
        not_overdue.save()
        self.assertEqual(0, self.scrapers.count())

    def testOverdue(self):
        # Scrapers that haven't been run for longer than the run interval
        # should appear in the list of scrapers to be run
        overdue = Scraper(last_run=datetime.datetime.now() - datetime.timedelta(7), 
                          run_interval=86400)
        overdue.save()
        self.assertEqual(1, self.scrapers.count())
