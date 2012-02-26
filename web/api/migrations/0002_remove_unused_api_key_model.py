# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'api_key'
        db.delete_table('api_api_key')


    def backwards(self, orm):
        
        # Adding model 'api_key'
        db.create_table('api_api_key', (
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=32, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('api', ['api_key'])


    models = {
        
    }

    complete_apps = ['api']
