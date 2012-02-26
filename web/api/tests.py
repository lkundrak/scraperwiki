from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

import frontend
import json
from codewiki.models import Scraper, Code

class APIViewsTests(TestCase):
    fixtures = ['test_data']

    def test_scraper_search(self):
        scrapers = Code.objects.filter(title__icontains="test")
        response = self.client.get(reverse('api:method_search'), {'query':'test scraper'}) #'query':'test', 'format':'csv'}))

        # print "---------", response.content
        self.assertEqual(response.status_code, 200)
        r = json.loads(response.content)
        self.assertEqual(len(r), 1)
        scraper_details = r[0]

        self.assertEqual(scraper_details['short_name'], 'test_scraper')
    
#    def test_user_search(self):
#        scrapers = Code.objects.filter(title__icontains="Generalpurpose")
#        response = self.client.get(reverse('search', kwargs={'q':'test'}))
#        self.assertEqual(response.status_code, 200)
#        self.assertEqual(response.context['users_num_results'], 1)
    



