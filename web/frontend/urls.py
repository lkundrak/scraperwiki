from django.conf.urls.defaults import *

from profiles import views as profile_views  # a not very well namespaced django plugin class
from contact_form.views import contact_form
import frontend.views as frontend_views  # who thinks replacing dots with underscores here is useful?? --JT
import frontend.forms as frontend_forms

from django.views.generic.simple import redirect_to, direct_to_template
from frontend.models import Feature

urlpatterns = patterns('',

    # profiles
    url(r'^profiles/edit/$', profile_views.edit_profile, {'form_class': frontend_forms.UserProfileForm}, name='profiles_edit_profile'),
    url(r'^profiles/(?P<username>.*)/message/$', frontend_views.user_message, name='user_message'),
    url(r'^profiles/(?P<username>.*)/$', frontend_views.profile_detail, name='profiles_profile_detail'),
    #url(r'^profiles/', include('profiles.urls')), 

    url(r'^login/$',frontend_views.login, name='login'),
    url(r'^login/confirm/$', direct_to_template, {'template': 'registration/confirm_account.html'}, name='confirm_account'),
    url(r'^terms_and_conditions/$', direct_to_template, {'template': 'frontend/terms_and_conditions.html'}, name='terms'),
    url(r'^privacy/$', direct_to_template, {'template': 'frontend/privacy.html'}, name='privacy'),
    url(r'^about/$', direct_to_template, {'template': 'frontend/about.html'}, name='about'),
    url(r'^tour/$', direct_to_template, {'template': 'frontend/tour.html'}, name='tour'),                                          
    url(r'^example_data/$', direct_to_template, {'template': 'frontend/example_data.html'}, name='api'),
    url(r'^pricing/$', frontend_views.pricing, name='pricing'),
    url(r'^subscribe/$', redirect_to, {'url': '/pricing/'}),
    url(r'^subscribe/(?P<plan>individual|business|corporate)/$', frontend_views.subscribe, name='subscribe'),
    url(r'^confirm_subscription/$', frontend_views.confirm_subscription, name='confirm_subscription'),


    url(r'^help/(?P<mode>intro|faq|tutorials|documentation|code_documentation|libraries)/(?P<language>python|php|ruby|javascript)/$','django.views.generic.simple.redirect_to', {'url': '/docs/%(language)s'},name='help'),
    url(r'^help/(?P<mode>intro|faq|tutorials|documentation|code_documentation|libraries)/$','django.views.generic.simple.redirect_to', {'url': '/docs/'}, name='help_default'),
    url(r'^help/$','django.views.generic.simple.redirect_to', {'url': '/docs/'}, name='help_default'),
    
    url(r'^get_involved/$',frontend_views.get_involved, name='get_involved'),
    url(r'^request_data/$',frontend_views.request_data, name='request_data'),
    url(r'^request_data/thanks/$',frontend_views.request_data_thanks, name='request_data_thanks'),
    
    #hello world
    url(r'^hello_world.html', direct_to_template, {'template': 'frontend/hello_world.html'}, name='help_hello_world'),

    # contact form
    url(r'^contact/$', contact_form, {'form_class': frontend_forms.ScraperWikiContactForm}, name='contact_form'),
    url(r'^contact/sent/$', direct_to_template, {'template': 'contact_form/contact_form_sent.html'}, name='contact_form_sent'),
    
    # user's scrapers
    url(r'^vaults/(?P<vaultid>\d+)/transfer/(?P<username>.*)/$', frontend_views.transfer_vault, name='transfer_vault'),                    
    url(r'^vaults/(?P<vaultid>\d+)/(?P<action>adduser|removeuser)/(?P<username>.*)/$', frontend_views.vault_users, name='vault_user'),        
    url(r'^vaults/(?P<vaultid>\d+)/addscraper/(?P<shortname>.*)/$', frontend_views.vault_scrapers_add, name='vault_scrapers_add'),            
    url(r'^vaults/(?P<vaultid>\d+)/removescraper/(?P<shortname>.*)/(?P<newstatus>public|visible)$', frontend_views.vault_scrapers_remove, name='vault_scrapers_remove'),                
    url(r'^vaults/$', frontend_views.view_vault, name='vault'),    
    url(r'^vaults/new/$', frontend_views.new_vault, name='new_vault'),    
    
    # this (?P<page_number>\d+) thing doesn't actually do anything, you know that right??
    url(r'^dashboard/?(?P<privacy_status>(?:non)?private)?/?(?P<page_number>\d+)?$', frontend_views.dashboard, name='dashboard'),
    url(r'^stats/$',                  frontend_views.stats, name='stats'),    
    
    # Example pages to scrape :)
    url(r'^examples/basic_table\.html$', direct_to_template, {'template': 'examples/basic_table.html'}, name='example_basic_table'),
    # for testing error handling
    url(r'^test_error/$',                  frontend_views.test_error, name='test_error'),    
    
    #searching and browsing
    url(r'^search/$', frontend_views.search, name='search'),
    url(r'^search/(?P<q>.+)/$', frontend_views.search, name='search'),

    url(r'^browse/(?P<page_number>\d+)?$', frontend_views.browse, name='scraper_list'),    
    url(r'^browse/(?P<wiki_type>scraper|view)s/(?P<page_number>\d+)?$', frontend_views.browse_wiki_type, name='scraper_list_wiki_type'),
    url(r'^tags/$', frontend_views.tags, name='all_tags'),    
    url(r'^tags/(?P<tag>[^/]+)$', frontend_views.tag, name='single_tag'),  
    
    #events
    url(r'^events/(?P<e>[^/]+)?/?$', frontend_views.events, name='events'),
    
    # corporate minisite
    url(r'corporate/', frontend_views.corporate, name='corporate'),
    
)
