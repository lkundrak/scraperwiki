# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'DataEnquiry.category'
        db.delete_column('frontend_dataenquiry', 'category')

        # Deleting field 'DataEnquiry.due_date'
        db.delete_column('frontend_dataenquiry', 'due_date')

        # Deleting field 'DataEnquiry.first_name'
        db.delete_column('frontend_dataenquiry', 'first_name')

        # Deleting field 'DataEnquiry.last_name'
        db.delete_column('frontend_dataenquiry', 'last_name')

        # Deleting field 'DataEnquiry.why'
        db.delete_column('frontend_dataenquiry', 'why')

        # Deleting field 'DataEnquiry.broadcast'
        db.delete_column('frontend_dataenquiry', 'broadcast')

        # Deleting field 'DataEnquiry.application'
        db.delete_column('frontend_dataenquiry', 'application')

        # Deleting field 'DataEnquiry.frequency'
        db.delete_column('frontend_dataenquiry', 'frequency')

        # Deleting field 'DataEnquiry.company_name'
        db.delete_column('frontend_dataenquiry', 'company_name')

        # Deleting field 'DataEnquiry.urls'
        db.delete_column('frontend_dataenquiry', 'urls')

        # Deleting field 'DataEnquiry.telephone'
        db.delete_column('frontend_dataenquiry', 'telephone')

        # Deleting field 'DataEnquiry.visualisation'
        db.delete_column('frontend_dataenquiry', 'visualisation')

        # Deleting field 'DataEnquiry.columns'
        db.delete_column('frontend_dataenquiry', 'columns')

        # Adding field 'DataEnquiry.name'
        db.add_column('frontend_dataenquiry', 'name', self.gf('django.db.models.fields.CharField')(default='', max_length=64), keep_default=False)

        # Adding field 'DataEnquiry.phone'
        db.add_column('frontend_dataenquiry', 'phone', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True), keep_default=False)

        # Changing field 'DataEnquiry.email'
        db.alter_column('frontend_dataenquiry', 'email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True))

        # Changing field 'DataEnquiry.description'
        db.alter_column('frontend_dataenquiry', 'description', self.gf('django.db.models.fields.TextField')(default=''))


    def backwards(self, orm):
        
        # User chose to not deal with backwards NULL issues for 'DataEnquiry.category'
        raise RuntimeError("Cannot reverse this migration. 'DataEnquiry.category' and its values cannot be restored.")

        # Adding field 'DataEnquiry.due_date'
        db.add_column('frontend_dataenquiry', 'due_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True), keep_default=False)

        # User chose to not deal with backwards NULL issues for 'DataEnquiry.first_name'
        raise RuntimeError("Cannot reverse this migration. 'DataEnquiry.first_name' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'DataEnquiry.last_name'
        raise RuntimeError("Cannot reverse this migration. 'DataEnquiry.last_name' and its values cannot be restored.")

        # Adding field 'DataEnquiry.why'
        db.add_column('frontend_dataenquiry', 'why', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Adding field 'DataEnquiry.broadcast'
        db.add_column('frontend_dataenquiry', 'broadcast', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Adding field 'DataEnquiry.application'
        db.add_column('frontend_dataenquiry', 'application', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # User chose to not deal with backwards NULL issues for 'DataEnquiry.frequency'
        raise RuntimeError("Cannot reverse this migration. 'DataEnquiry.frequency' and its values cannot be restored.")

        # Adding field 'DataEnquiry.company_name'
        db.add_column('frontend_dataenquiry', 'company_name', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True), keep_default=False)

        # User chose to not deal with backwards NULL issues for 'DataEnquiry.urls'
        raise RuntimeError("Cannot reverse this migration. 'DataEnquiry.urls' and its values cannot be restored.")

        # Adding field 'DataEnquiry.telephone'
        db.add_column('frontend_dataenquiry', 'telephone', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True), keep_default=False)

        # Adding field 'DataEnquiry.visualisation'
        db.add_column('frontend_dataenquiry', 'visualisation', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Adding field 'DataEnquiry.columns'
        db.add_column('frontend_dataenquiry', 'columns', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Deleting field 'DataEnquiry.name'
        db.delete_column('frontend_dataenquiry', 'name')

        # Deleting field 'DataEnquiry.phone'
        db.delete_column('frontend_dataenquiry', 'phone')

        # Changing field 'DataEnquiry.email'
        db.alter_column('frontend_dataenquiry', 'email', self.gf('django.db.models.fields.EmailField')(default='', max_length=75))

        # Changing field 'DataEnquiry.description'
        db.alter_column('frontend_dataenquiry', 'description', self.gf('django.db.models.fields.TextField')(null=True))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'frontend.dataenquiry': {
            'Meta': {'object_name': 'DataEnquiry'},
            'date_of_enquiry': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'frontend.feature': {
            'Meta': {'ordering': "['name']", 'object_name': 'Feature'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'frontend.message': {
            'Meta': {'object_name': 'Message'},
            'finish': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'frontend.userprofile': {
            'Meta': {'ordering': "('-created_at',)", 'object_name': 'UserProfile'},
            'apikey': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'beta_user': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'features': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'features'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['frontend.Feature']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'messages': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'plan': ('django.db.models.fields.CharField', [], {'default': "'free'", 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['frontend']
