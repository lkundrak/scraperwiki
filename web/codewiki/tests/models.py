from django.test import TestCase

from codewiki.models import Scraper, UserUserRole
from django.contrib.auth.models import User

class Test__unicode__(TestCase):
    def test_scraper_name(self):
        self.assertEqual(
            'test_scraper',
            unicode(Scraper(title='Test Scraper', short_name='test_scraper'))
        )

class TestUserUserRole(TestCase):
    fixtures = ['test_data.json']

    def test_no_link_by_default(self):
        # s = Scraper.objects.get(short_name='test_scraper')
        u1 = User.objects.get(username='test_user')
        u2 = User.objects.get(username='test_admin')

        self.assertEqual(len(u1.useruserrole_set.all()), 0)
        self.assertEqual(len(u2.useruserrole_set.all()), 0)

    def test_making_removing_team_link(self):
        u1 = User.objects.get(username='test_user')
        u2 = User.objects.get(username='test_admin')

        UserUserRole.put_on_team(u1, u2)
        self.assertEqual([ x.other for x in u1.useruserrole_set.all() ], [u2])
        self.assertEqual([ x.user for x in u2.rev_useruserrole_set.all() ], [u1])

        UserUserRole.remove_from_team(u1, u2)
        self.assertEqual(len(u1.useruserrole_set.all()), 0)
        self.assertEqual(len(u2.useruserrole_set.all()), 0)



