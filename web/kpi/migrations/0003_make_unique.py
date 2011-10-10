
from south.db import db
from django.db import models
from kpi.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Creating unique_together for [date] on MonthlyCounts.
        db.create_unique('kpi_monthlycounts', ['date'])
        
        # Creating unique_together for [date] on DatastoreRecordCount.
        db.create_unique('kpi_datastorerecordcount', ['date'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [date] on DatastoreRecordCount.
        db.delete_unique('kpi_datastorerecordcount', ['date'])
        
        # Deleting unique_together for [date] on MonthlyCounts.
        db.delete_unique('kpi_monthlycounts', ['date'])
        
    
    
    models = {
        'kpi.datastorerecordcount': {
            'date': ('django.db.models.fields.DateField', [], {'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {})
        },
        'kpi.monthlycounts': {
            'active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'unique': 'True'}),
            'delta_active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'this_months_scrapers': ('django.db.models.fields.IntegerField', [], {}),
            'this_months_users': ('django.db.models.fields.IntegerField', [], {}),
            'this_months_views': ('django.db.models.fields.IntegerField', [], {}),
            'total_scrapers': ('django.db.models.fields.IntegerField', [], {}),
            'total_users': ('django.db.models.fields.IntegerField', [], {}),
            'total_views': ('django.db.models.fields.IntegerField', [], {})
        }
    }
    
    complete_apps = ['kpi']
