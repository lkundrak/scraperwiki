# encoding: utf-8
import datetime
import time
import code
import scraper
import os

# Development note:  Aiming to merge scraper,view,code back into one object

from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.urlresolvers import reverse

try:
    import json
except:
    import simplejson as json

class View(code.Code):
    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)
        self.wiki_type = 'view'        

    def save(self, *args, **kwargs):
        first_save = not self.id 

        super(View, self).save(*args, **kwargs)

        if first_save and self.forked_from:
            for scraper in self.forked_from.relations.all():
                if scraper not in self.relations.all():
                    self.relations.add(scraper)

    def get_screenshot_url(self, url_prefix):
        return '%s%s' % (url_prefix, reverse('rpcexecute', args=[self.short_name]))

    def content_type(self):
        return ContentType.objects.get(app_label="codewiki", model="View")

    class Meta:
        app_label = 'codewiki'


