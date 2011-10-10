from django.conf.urls.defaults import patterns, url

from api import viewshandlers
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse

try:    import json
except: import simplejson as json


# Version 1.0 URLS
urlpatterns = patterns('',
    
    # current api
    url(r'^1\.0/datastore/sqlite$',     viewshandlers.sqlite_handler,         name="method_sqlite"),
    url(r'^1\.0/scraper/search$',       viewshandlers.scraper_search_handler, name="method_search"),
    url(r'^1\.0/scraper/getuserinfo$',  viewshandlers.userinfo_handler,       name="method_getuserinfo"),
    url(r'^1\.0/scraper/usersearch$',   viewshandlers.usersearch_handler,     name="method_usersearch"),
    url(r'^1\.0/scraper/getruninfo$',   viewshandlers.runevent_handler,       name="method_getruninfo"),
    url(r'^1\.0/scraper/getinfo$',      viewshandlers.scraperinfo_handler,    name="method_getinfo"),

    # deprecated api
    url(r'^1\.0/datastore/search$', lambda request: HttpResponse(json.dumps({ "error":"Sorry, this function has been deprecated.", "message":"no search is possible across different databases" }))),
    url(r'^1\.0/datastore/getkeys$', lambda request: HttpResponse(json.dumps({ "error":"Sorry, this function has been deprecated.", "message":"use scraperwiki.datastore.sqlite with format=jsonlist and limit 0" }))),
    url(r'^1\.0/datastore/getdatabydate$', lambda request: HttpResponse(json.dumps({ "error":"Sorry, this function has been deprecated.", "message":"use scraperwiki.datastore.sqlite with bounds on your date field" }))),
    url(r'^1\.0/datastore/getdatabylocation$', lambda request: HttpResponse(json.dumps({ "error":"Sorry, this function has been deprecated.", "message":"use scraperwiki.datastore.sqlite bounds on the lat lng values" }))),
    url(r'^1\.0/geo/postcodetolatlng/$', lambda request: HttpResponse(json.dumps({ "error":"Sorry, this function has been deprecated.", "message":"use the scraperwiki postcode view to do it" }))),
    url(r'^1\.0/datastore/getdata$',    lambda request: HttpResponse(json.dumps({ "error":"Sorry, this function has been deprecated.", "message":"use the scraperwiki sqlite api to do it" }))),
        
    # explorer redirects
    url(r'^1\.0/explore/scraperwiki.(?:scraper|datastore).(?P<shash>\w+)$', 
                   lambda request, shash: HttpResponseRedirect("%s#%s" % (reverse('docsexternal'), shash))),
    url(r'^(?:1\.0|1\.0/explore/.*|)$', 
                   lambda request: HttpResponseRedirect(reverse('docsexternal'))),

)
