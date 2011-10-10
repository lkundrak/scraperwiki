# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'datastorerecordcount.id'
        db.delete_column('kpi_datastorerecordcount', 'id')

        # Changing field 'DatastoreRecordCount.date'
        db.alter_column('kpi_datastorerecordcount', 'date', self.gf('django.db.models.fields.DateField')(primary_key=True))

        # Deleting field 'monthlycounts.id'
        db.delete_column('kpi_monthlycounts', 'id')

        # Adding field 'MonthlyCounts.longtime_active_coders'
        db.add_column('kpi_monthlycounts', 'longtime_active_coders', self.gf('django.db.models.fields.IntegerField')(default=-1), keep_default=False)

        # Adding field 'MonthlyCounts.delta_longtime_active_coders'
        db.add_column('kpi_monthlycounts', 'delta_longtime_active_coders', self.gf('django.db.models.fields.IntegerField')(default=-1), keep_default=False)

        # Changing field 'MonthlyCounts.date'
        db.alter_column('kpi_monthlycounts', 'date', self.gf('django.db.models.fields.DateField')(primary_key=True))


    def backwards(self, orm):
        
        # User chose to not deal with backwards NULL issues for 'datastorerecordcount.id'
        raise RuntimeError("Cannot reverse this migration. 'datastorerecordcount.id' and its values cannot be restored.")

        # Changing field 'DatastoreRecordCount.date'
        db.alter_column('kpi_datastorerecordcount', 'date', self.gf('django.db.models.fields.DateField')(unique=True))

        # User chose to not deal with backwards NULL issues for 'monthlycounts.id'
        raise RuntimeError("Cannot reverse this migration. 'monthlycounts.id' and its values cannot be restored.")

        # Deleting field 'MonthlyCounts.longtime_active_coders'
        db.delete_column('kpi_monthlycounts', 'longtime_active_coders')

        # Deleting field 'MonthlyCounts.delta_longtime_active_coders'
        db.delete_column('kpi_monthlycounts', 'delta_longtime_active_coders')

        # Changing field 'MonthlyCounts.date'
        db.alter_column('kpi_monthlycounts', 'date', self.gf('django.db.models.fields.DateField')(unique=True))


    models = {
        'kpi.datastorerecordcount': {
            'Meta': {'object_name': 'DatastoreRecordCount'},
            'date': ('django.db.models.fields.DateField', [], {'primary_key': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {})
        },
        'kpi.monthlycounts': {
            'Meta': {'object_name': 'MonthlyCounts'},
            'active_coders': ('django.db.models.fields.IntegerField', [], {}),
            'date': ('django.db.models.fields.DateField', [], {'primary_key': 'True'}),
            'delta_active_coders': ('django.db.models.fields.IntegerField', [], {}),
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
