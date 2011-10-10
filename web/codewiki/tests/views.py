"""
At the moment, this only tests some codewiki.views
"""

from django.core.urlresolvers import reverse
from django.test import TestCase

import codewiki

class ScraperViewsTests(TestCase):
    fixtures = ['test_data.json']
    
    def test_scraper_list(self):
        """
        test
        """
        response = self.client.get(reverse('scraper_list'))
        self.assertEqual(response.status_code, 200)
        
    def test_scraper_overview(self):
        response = self.client.get(reverse('code_overview', 
                            kwargs={'wiki_type':'scraper', 'short_name': 'test_scraper'}))
        self.assertEqual(response.status_code, 200)
    
    
    def _ensure_repo_exists( self, name ):
        """
        Check whether the repo exists, and create it if it does not. This is only used
        for testing and so should be safe.
        """
        from codewiki.vc import MercurialInterface
        from django.conf import settings
        from codewiki.models.scraper import Scraper
        from codewiki.models.code import Code

        s = Code.objects.get(short_name=name)
        m = s.vcs

        try:
            status = m.getfilestatus( )
        except:
            s.commit_code('# Scraper for automated testing purposes only', 'This is an automated test commit.', s.owner())
            #print "\nrepository for scraper '%s' created in dir '%s'" % (name, s.get_repo_path())
    
    
    def test_scraper_history(self):
        self._ensure_repo_exists( 'test_scraper')
            
        response = self.client.get(reverse('scraper_history',
                            kwargs={'wiki_type':'scraper', 'short_name': 'test_scraper'}))
        self.assertEqual(response.status_code, 200)
        
    
    def test_scraper_comments(self):
        self._ensure_repo_exists( 'test_scraper')
            
        response = self.client.get(reverse('scraper_comments',
                            kwargs={'wiki_type':'scraper', 'short_name': 'test_scraper'}))
        self.assertEqual(response.status_code, 200)

    def test_scraper_all_tags(self):
        response = self.client.get(reverse('all_tags'))
        self.assertEqual(response.status_code, 200)

    def test_scraper_search(self):
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('search', kwargs={'q': 'test'}))
        self.assertEqual(response.status_code, 200)


