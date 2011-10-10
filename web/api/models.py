# encoding: utf-8
import datetime
import time

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

from codewiki.models import Code

class APIMetric(models.Model):
    """
    Simple metrics for API class so that we can track their usage. We have optional
    code (scraper/view) and user objects if we know what they are when we record the 
    usage.
    """
    # Optional user/code if known  - + means no backward relation in the foreign class
    user        = models.ForeignKey(User, related_name='+', null=True)
    code_object = models.ForeignKey(Code, related_name='+', null=True)
    
    # The API call that was made
    apicall     = models.CharField(max_length=64, null=False, blank=False)
    
    # The key data involved in the call, search term etc.
    key_data    = models.CharField(max_length=100, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    
    @staticmethod
    def record( apicall, key_data=None, user=None, code_object=None ):
        m = APIMetric( apicall=apicall, key_data=key_data, user=user, code_object=code_object )
        m.save()
