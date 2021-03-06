from django.conf.urls.defaults import patterns, url
from documentation import views

urlpatterns = patterns('',
   url(r'^(?:(?P<language>(python|ruby|php|perl|html|javascript))/)?$', views.docmain, name="docsroot"),
   url(r'^api_explorer___$',                views.api_explorer, name="api_explore"),
   url(r'^api$',                            views.docsexternal, name="docsexternal"),
   url(r'^contrib/(?P<short_name>[\w_\-\./]+)/$', views.contrib, name="docscontrib"),
   url(r'^(?P<language>(python|ruby|php|perl))/$',views.docmain, name="docs"),
   url(r'^tutorials/$',views.tutorials, name="tutorials"),            
   url(r'^(?P<language>(python|ruby|php|perl|shared|html|javascript))/tutorials/$',views.tutorials, name="tutorials"),
   url(r'^(?P<language>(python|ruby|php|perl|shared|html|javascript))/(?P<path>[\w_\-\.]+)/$',views.docmain, name="docs"),
   url(r'^(?P<path>([\w_\-\.]+|/))/$',    views.docmain, name="docs"),   
)
