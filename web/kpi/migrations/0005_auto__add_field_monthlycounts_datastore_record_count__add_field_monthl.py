# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'MonthlyCounts.datastore_record_count'
        db.add_column('kpi_monthlycounts', 'datastore_record_count', self.gf('django.db.models.fields.IntegerField')(default=-1), keep_default=False)

        # Adding field 'MonthlyCounts.delta_datastore_record_count'
        db.add_column('kpi_monthlycounts', 'delta_datastore_record_count', self.gf('django.db.models.fields.IntegerField')(default=-1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'MonthlyCounts.datastore_record_count'
        db.delete_column('kpi_monthlycounts', 'datastore_record_count')

        # Deleting field 'MonthlyCounts.delta_datastore_record_count'
        db.delete_column('kpi_monthlycounts', 'delta_datastore_record_count')


    models = {
        'kpi.datastorerecordcount': {
            'Meta': {'object_name': 'DatastoreRecordCount'},
            'date': ('django.db.models.fields.DateField', [], {'primary_key': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {})
        },
        'kpi.monthlycounts': {
            'Meta': {'object_name': 'MonthlyCounts'},
            'active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'datastore_record_count': ('django.db.models.fields.IntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'primary_key': 'True'}),
            'delta_active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'delta_datastore_record_count': ('django.db.models.fields.IntegerField', [], {}),
            'delta_longtime_active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'longtime_active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'this_months_scrapers': ('django.db.models.fields.IntegerField', [], {}),
            'this_months_users': ('django.db.models.fields.IntegerField', [], {}),
            'this_months_views': ('django.db.models.fields.IntegerField', [], {}),
            'total_scrapers': ('django.db.models.fields.IntegerField', [], {}),
            'total_users': ('django.db.models.fields.IntegerField', [], {}),
            'total_views': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['kpi']
