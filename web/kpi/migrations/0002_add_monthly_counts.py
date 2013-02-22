
from south.db import db
from django.db import models
from kpi.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'MonthlyCounts'
        db.create_table('kpi_monthlycounts', (
            ('id', orm['kpi.monthlycounts:id']),
            ('date', orm['kpi.monthlycounts:date']),
            ('total_scrapers', orm['kpi.monthlycounts:total_scrapers']),
            ('this_months_scrapers', orm['kpi.monthlycounts:this_months_scrapers']),
            ('total_views', orm['kpi.monthlycounts:total_views']),
            ('this_months_views', orm['kpi.monthlycounts:this_months_views']),
            ('total_users', orm['kpi.monthlycounts:total_users']),
            ('this_months_users', orm['kpi.monthlycounts:this_months_users']),
            ('active_coders', orm['kpi.monthlycounts:active_coders']),
            ('delta_active_coders', orm['kpi.monthlycounts:delta_active_coders']),
        ))
        db.send_create_signal('kpi', ['MonthlyCounts'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'MonthlyCounts'
        db.delete_table('kpi_monthlycounts')
        
    
    
    models = {
        'kpi.datastorerecordcount': {
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {})
        },
        'kpi.monthlycounts': {
            'active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {}),
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
