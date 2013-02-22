# encoding: utf-8
import datetime
import time

# Development note:  Aiming to merge scraper,view,code back into one object

from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.urlresolvers import reverse

from codewiki import managers
from django.db.models.signals import post_save
from registration.signals import user_registered

from frontend import models as frontendmodels

from codewiki.managers.datastore import DataStore

import codewiki.util
import codewiki.vc
import code
import view
import urllib2

import logging

try:
    import json
except:
    import simplejson as json

# for now till we establish logging into the django system
logger = logging

SCHEDULE_OPTIONS =  (
                    (-1, 'never', 'Don&rsquo;t schedule', 'No schedule set'), 
                    (3600*24*31, 'monthly', 'Run every month', 'Runs every month'),
                    (3600*24*7, 'weekly', 'Run every week', 'Runs every week'),
                    (3600*24, 'daily', 'Run every day', 'Runs every day'),
                    (3600, 'hourly', 'Run every hour', 'Runs every hour')
                    )


    # unfortunately has to be a scrapers list because run_interval and last_run not available to code objects
def scrapers_overdue():
    """
    Obtains a queryset of scrapers that should have already been run, we 
    will order these with the ones that have run least recently hopefully
    being near the top of the list.
    """
    scrapers = Scraper.objects.exclude(privacy_status="deleted")
    scrapers = scrapers.filter(run_interval__gt=0)
    
    qselect = {}
    qselect["secondsto_nextrun"] = "IF(run_interval>0, IF(last_run is not null, TIMESTAMPDIFF(SECOND, NOW(), DATE_ADD(last_run, INTERVAL run_interval SECOND)), 0), 99999)"
    qselect["overdue_proportion"] = "IF(run_interval>0, IF(last_run is not null, TIMESTAMPDIFF(SECOND, NOW(), DATE_ADD(last_run, INTERVAL run_interval SECOND))/run_interval, -1.0), 1.0)"
    qwhere = ["(last_run is null or DATE_ADD(last_run, INTERVAL run_interval SECOND) < NOW())"]
    
    scrapers = scrapers.extra(select=qselect, where=qwhere)
    scrapers = scrapers.order_by('overdue_proportion')
    
    return scrapers


class Scraper (code.Code):
    last_run     = models.DateTimeField(blank=True, null=True)    
    record_count = models.IntegerField(default=0)        
    # In seconds; default to disabled.
    run_interval = models.IntegerField(default=-1)

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)
        self.wiki_type = 'scraper'

    # :todo: It would be good to kill this function off and move
    # its functionality into being properties of the database.
    # For now it represents some kind of caching of the size
    # of the datastore.
    def update_meta(self):
        dataproxy = DataStore(self.short_name)
        try:
            newcount = 0
            datasummary = dataproxy.request({"maincommand":"sqlitecommand", "command":"datasummary", "limit":-1})
            if "error" not in datasummary:
                if 'total_rows' in datasummary:
                    self.record_count = datasummary['total_rows']
                else:
                    for tabledata in datasummary.get("tables", {}).values():
                        newcount += tabledata["count"]
                    
                    # Only update the record count when we have definitely not failed.
                    self.record_count = newcount                   
            else:
                print "logthis", datasummary                
        except Exception, e:
            print "logthis", e
        finally:
            try:
                dataproxy.close()
            except:
                pass

    def content_type(self):
        return ContentType.objects.get(app_label="codewiki", model="Scraper")

    # perhaps should be a member variable so we can sort directly on it (and set it when we want something to run immediately)
    def next_run(self):
        if not self.run_interval or self.run_interval == -1:
            return datetime.datetime(9999, 12, 31)
        if not self.last_run:
            return datetime.datetime.now() - datetime.timedelta(1, 0, 0)  # one day ago
        return self.last_run + datetime.timedelta(0, self.run_interval, 0)

    def get_screenshot_url(self, view_url_prefix = settings.VIEW_URL):
        try:
            url = self.scraperrunevent_set.latest('run_started').first_url_scraped
        except:
            url = None

        if url:
            if url.endswith('robots.txt'):
                url = url.replace('robots.txt', '')
            return url

        # show shot of the editor if there is no URL
        return '%s%s' % (view_url_prefix, reverse('editor_edit', args=[self.wiki_type, self.short_name]))

    class Meta:
        app_label = 'codewiki'

        
class ScraperRunEvent(models.Model):
    scraper           = models.ForeignKey(Scraper)
    
    # attempts to migrate this to point to a code object involved
    # adding in the new field
    #     code              = models.ForeignKey(code.Code,
    #                           null=True, related_name="+")
    # and then data migrating over to it with 
    #     scraperrunevent.code = Code.filter(
    #        pk=scraperrunevent.scraper.pk) 
    # in a loop over all scrapers, (though this crashed and ran out
    # of memory at a limit of 2000) before abolishing the scraper
    # parameter.
    
    run_id            = models.CharField(max_length=100, db_index=True, blank=True, null=True)
    # Will only be temporarily valid and probably doesn't belong here.
    pid               = models.IntegerField()
    run_started       = models.DateTimeField(db_index=True)
    
    # missnamed. used as last_updated so you can see if the scraper
    # is hanging.
    run_ended         = models.DateTimeField(null=True)   
    records_produced  = models.IntegerField(default=0)
    pages_scraped     = models.IntegerField(default=0)
    output            = models.TextField()
    first_url_scraped = models.CharField(max_length=256, blank=True, null=True)
    exception_message = models.CharField(max_length=256, blank=True, null=True)
    revision          = models.CharField(max_length=64, blank=True, null=True)    
    # True when this runevent has been notifed, by sending an
    # email.  Typically only runevents in vault are notified,
    # and only when they have an exception and are the most revent
    # runevent of a scraper.
    notified          = models.BooleanField(default=False)

    def __unicode__(self):
        res = [u'start: %s' % self.run_started]
        if self.run_ended:
            res.append(u'end: %s' % self.run_ended)
        if self.exception_message:
            res.append(u'exception: %s' % self.exception_message)
        return u'  '.join(res)

    def outputsummary(self):
        return u'records=%d scrapedpages=%d outputlines=%d' % (self.records_produced, self.pages_scraped, self.output.count('\n'))

    def getduration(self):
        return (self.run_ended or datetime.datetime.now()) - self.run_started
    def getdurationseconds(self):
        runduration = self.getduration()
        return "%.0f" % (runduration.days*24*60*60 + runduration.seconds)

    @models.permalink
    def get_absolute_url(self):
        return ('run_event', [self.run_id])

    def set_notified(self):
        self.notified = True
        self.save()

    class Meta:
        app_label = 'codewiki'

class DomainScrape(models.Model):
    """
    Record of a domain that was scraped by a run event
    """
    scraper_run_event = models.ForeignKey(ScraperRunEvent)
    domain            = models.CharField(max_length=128)
    bytes_scraped     = models.IntegerField(default=0)
    pages_scraped     = models.IntegerField(default=0)

    def __unicode__(self):
        return u'domain: %s (pages %d, bytes %d) for %s' % (self.domain, self.pages_scraped, self.bytes_scraped, self.scraper_run_event.scraper.short_name)

    class Meta:
        app_label = 'codewiki'
