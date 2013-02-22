from django.conf.urls.defaults import patterns, url
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

import cropper.views

urlpatterns = patterns('',
   url(r'^$',                                          cropper.views.cropdoc,  name="cropdoc"), 
   url(r'^(?P<srcdoc>(?:t\.\w+|u))/page_(?P<page>\d+)/(?P<cropping>.+?/)?$',      
                                                       cropper.views.croppage, name="croppage"), 
   url(r'^(?P<format>png|pngprev)/(?P<srcdoc>(?:t\.\w+|u))/page_(?P<page>\d+)/(?P<cropping>.+?/)?$', 
                                                       cropper.views.cropimg,  name="cropimg"), 
   )
   
   
