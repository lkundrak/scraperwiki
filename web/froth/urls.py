from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^check_key/(?P<apikey>.*[^/])/?$', 'froth.views.check_key'),
)
