"""
At the moment, this only tests some frontend.views
"""

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.core import mail

from captcha.models import CaptchaStore

import frontend
from codewiki.models import Scraper, Code

class FrontEndViewsTests(TestCase):
    fixtures = ['./fixtures/test_data.json']
    
    def setUp(self):
        # make a dummy user...
        user = User(username='test', password='123')
        user.save()
        
    def test_profile_edit(self):
        self.client.login(username='test', password='123')
        response = self.client.post(reverse('profiles_edit_profile',), 
                                    {'bio' : 'updated bio',
                                    'alert_frequency' : 99})
        self.assertEqual(response.status_code, 302)

    def test_profile_view(self):
        user = User(username='test')
        response = self.client.get(reverse('profiles_profile_detail', 
                                            kwargs={'username' : user}))
        self.assertEqual(response.status_code, 200)

    def test_login(self):
        response = self.client.post(reverse('login'), {'username': 'test',
                                                       'password': '123'})
        self.assertEqual(response.status_code, 200)

    def test_terms(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)

    def test_privacy(self):
        response = self.client.get(reverse('privacy'))
        self.assertEqual(response.status_code, 200)

    def test_about(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

class FrontEndViewsDocumentationTests(TestCase):
    def test_docs_ruby(self):
        response = self.client.get(reverse('docs', kwargs={'language': 'ruby'}))
        self.assertEqual(response.status_code, 200)

    def test_docs_python(self):
        response = self.client.get(reverse('docs', kwargs={'language': 'python'}))
        self.assertEqual(response.status_code, 200)

    def test_docs_php(self):
        response = self.client.get(reverse('docs', kwargs={'language': 'php'}))
        self.assertEqual(response.status_code, 200)

    def test_help(self):
        response = self.client.get('/help/', follow=True)
        self.assertEqual(response.redirect_chain, [('http://testserver/docs/', 301), ('http://testserver/docs/python/', 302)])

    def test_contact_form_with_captcha(self):
        self.failUnlessEqual(CaptchaStore.objects.count(), 0)
        response = self.client.get(reverse('contact_form'))
        self.assertEqual(response.status_code, 200)
        self.failUnlessEqual(CaptchaStore.objects.count(), 1)
        captcha = CaptchaStore.objects.all()[0]

        self.assertEquals(len(mail.outbox), 0)
        response = self.client.post(reverse('contact_form'), {
            'name': 'Mr. X Feedbacker', 'email': 'test_contact@django.scraperwiki.com',
            'title': 'Just checking your form works', 'subject_dropdown': 'help', 'body': 'Thanks for your help & all :)',
            'captcha_0': captcha.hashkey, 'captcha_1': captcha.response
        })
        print response.content
        self.assertRedirects(response, reverse('contact_form_sent'), status_code = 302, target_status_code = 200)

        # https://docs.djangoproject.com/en/dev/topics/email/#emailmessage-objects
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject, '[ScraperWiki Feedback] [help] Just checking your form works')
        self.assertEquals(mail.outbox[0].from_email, '"Mr. X Feedbacker" <test_contact@django.scraperwiki.com>')
        self.assertEquals(mail.outbox[0].body, 'Thanks for your help & all :)\n')

    def test_live_tutorials(self):    
        # make some dummy tutorials
        ix = 0 
        for lang in ['ruby', 'python', 'php']:
            ix = ix + 1
            for i in range(ix):
                scraper = Scraper(title=unicode(lang + str(i)), language=lang, istutorial=True)
                scraper.save()

        # check the pages render right
        ix = 0
        for lang in ['ruby', 'python', 'php']:
            ix = ix + 1

            response = self.client.get(reverse('tutorials', kwargs={'language':lang}))
            self.assertEqual(response.status_code, 200)

            tutorials = response.context['tutorials']
            # print "***TUT:", tutorials
            self.assertEqual(tutorials.keys(), [lang])
            self.assertEqual(ix, len(tutorials[lang]))

class FrontEndViewsSearchTests(TestCase):
    fixtures = ['test_data']

    def test_scraper_search(self):
        response = self.client.get(reverse('search', kwargs={'q':'test'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['scrapers_num_results'], 2)
    
    def test_user_search_by_human_name(self):
        response = self.client.get(reverse('search', kwargs={'q':'Generalpurpose'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['users_num_results'], 1)

    def test_user_search_by_unix_name(self):
        response = self.client.get(reverse('search', kwargs={'q':'test_admin'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['users_num_results'], 1)


#        scrapers = Code.objects.filter(title__icontains="test")
#        scrapers = Code.objects.filter(title__icontains="Generalpurpose")

