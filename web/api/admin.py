from django.contrib import admin
from django.db import models

from models import APIMetric


class APIMetricAdmin(admin.ModelAdmin):
    list_display = ('apicall', 'user', 'created_at')
    list_filter = ('apicall',)
    
    
admin.site.register(APIMetric, APIMetricAdmin)    