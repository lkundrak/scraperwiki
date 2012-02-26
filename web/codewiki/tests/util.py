# -*- coding: utf-8 -*-

from django.test import TestCase

from codewiki.util import SlugifyUniquely
from codewiki.models import Scraper

class ScraperUtilTests(TestCase):
    def test_short_name_several_same_long_name(self):
        long_title = u'I think this is a very very very very very very very long title'

        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')
        self.assertEqual(u'i_think_this_is_a_very_very_very_very_very_very_ve', short_name)

        scraper1 = Scraper()
        scraper1.title = long_title
        scraper1.save()

        self.assertEqual(short_name, scraper1.short_name)

        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')
        self.assertEqual(u'i_think_this_is_a_very_very_very_very_very_very_1', short_name)

        scraper2 = Scraper()
        scraper2.title = long_title
        scraper2.save()

        self.assertEqual(short_name, scraper2.short_name)

        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')
        self.assertEqual(u'i_think_this_is_a_very_very_very_very_very_very_2', short_name)

    def test_short_name_katakana(self):
        long_title = u'ギンレイホール'
        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')

        # check the slug for a Katakana only titled scraper isn't empty
        self.assertNotEqual(u'', short_name)

        # and (less importantly) check it comes out as 'u', which is what we do
        # at the moment (not reason it shouldn't change)
        self.assertEqual(u'u', short_name)

    def test_short_name_space_terminated(self):
        long_title = u'some name ending in a space '
        short_name = SlugifyUniquely(long_title, Scraper, 'short_name')

        self.assertEqual(u'some_name_ending_in_a_space', short_name)

