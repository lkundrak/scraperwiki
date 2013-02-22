#!/usr/bin/env
# coding=utf-8 pep-0263 ftw!
"""
At the moment, this only tests some codewiki.viewseditor
"""

from django.core.urlresolvers import reverse
from django.test import TestCase

import codewiki
from codewiki.models import Scraper, Code

import datetime
import json

test_new_scraper_params = {
        'title':'Saved directly from test suite',
        'commit_message':'cccommit',
        'sourcescraper':'',
        'fork':'',
        'wiki_type':'scraper',
        'guid':'',
        'language':'ruby',
        'code':'puts "this was made va ScraperViewsEditorTests.test_save_new"\n',
        'earliesteditor':'dummyearliesteditortimestring' # XXX should be some kind of date/time of editor session, but not sure of format
}

class ScraperViewsEditorTests(TestCase):
    fixtures = ['test_data.json']
    
    def test_raw_content(self):
        response = self.client.get(reverse('raw', kwargs={'short_name': 'test_scraper'}))
        self.assertEqual(response.status_code, 200)
        # Indicative for the "outré" bug, issue #954.
        self.assertIn('charset=utf-8', response['Content-Type'])
        
    def test_run_event_json(self):
        response = self.client.get(reverse('run_event_json', kwargs={'run_id':2}))
        self.assertEqual(response.status_code, 200)

    def test_save_new_draft(self):
        # when not logged in, it makes a draft scraper (i.e. does little)
        response = self.client.post(reverse('handle_editor_save'), test_new_scraper_params)
        resp = json.loads(response.content)
        self.assertEqual(resp, {"status": "OK", "url": "/scrapers/new/ruby", "draft": "True"})
        
    def test_fork_scraper(self):
        self.client.login(username='test_user', password='123456')
        s = Code.objects.get(short_name='test_scraper')

        # fork from a scraper with each permission to check it gets copied
        for privacy_status in ('public', 'visible', 'private'):
            s.privacy_status = privacy_status
            s.save()

            params = test_new_scraper_params.copy()
            params['fork'] = 'test_scraper'
            response = self.client.post(reverse('handle_editor_save'), params)
            self.assertEqual(response.status_code, 200)

            new_s = Scraper.objects.get(short_name = 'saved_directly_from_test_suite')
            self.assertEqual(new_s.forked_from, s)
            
    '''
    def test_save_new_logged_in(self):
        # when logged in ...
        self.client.login(username='test_user', password='123456')
        response = self.client.post(reverse('handle_editor_save'), test_new_scraper_params)

        # ... it makes a scraper
        resp = json.loads(response.content)
        self.assertEqual(resp["redirect"], "true"), 
        self.assertEqual(resp["url"], u"/scrapers/saved_directly_from_test_suite/edit/")
        self.assertEqual(resp["rev"], 0)
        # XXX revdateepoch is here and should be checked is sane

        # check we can get the scraper out
        new_s = Scraper.objects.get(short_name = 'saved_directly_from_test_suite')
'''
