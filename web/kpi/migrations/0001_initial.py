
from south.db import db
from django.db import models
from kpi.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'DatastoreRecordCount'
        db.create_table('kpi_datastorerecordcount', (
            ('id', orm['kpi.DatastoreRecordCount:id']),
            ('date', orm['kpi.DatastoreRecordCount:date']),
            ('record_count', orm['kpi.DatastoreRecordCount:record_count']),
        ))
        db.send_create_signal('kpi', ['DatastoreRecordCount'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'DatastoreRecordCount'
        db.delete_table('kpi_datastorerecordcount')
        
    
    
    models = {
        'kpi.datastorerecordcount': {
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {})
        }
    }
    
    complete_apps = ['kpi']
