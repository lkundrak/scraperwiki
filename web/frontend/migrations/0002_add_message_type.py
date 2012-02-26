
from south.db import db
from django.db import models
from frontend.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'AlertTypes'
        db.create_table('frontend_alerttypes', (
            ('id', orm['frontend.alerttypes:id']),
            ('name', orm['frontend.alerttypes:name']),
        ))
        db.send_create_signal('frontend', ['AlertTypes'])
        
        # Adding ManyToManyField 'UserProfile.alert_types'
        db.create_table('frontend_userprofile_alert_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userprofile', models.ForeignKey(orm.UserProfile, null=False)),
            ('alerttypes', models.ForeignKey(orm.AlertTypes, null=False))
        ))
        
        # Changing field 'UserProfile.alert_frequency'
        # (to signature: django.db.models.fields.IntegerField(null=True, blank=True))
        db.alter_column('frontend_userprofile', 'alert_frequency', orm['frontend.userprofile:alert_frequency'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'AlertTypes'
        db.delete_table('frontend_alerttypes')
        
        # Dropping ManyToManyField 'UserProfile.alert_types'
        db.delete_table('frontend_userprofile_alert_types')
        
        # Changing field 'UserProfile.alert_frequency'
        # (to signature: django.db.models.fields.IntegerField())
        db.alter_column('frontend_userprofile', 'alert_frequency', orm['frontend.userprofile:alert_frequency'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'frontend.alerttypes': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        'frontend.userprofile': {
            'alert_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'alert_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['frontend.AlertTypes']"}),
            'alerts_last_sent': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'frontend.usertouserrole': {
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'to_user'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'from_user'", 'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['frontend']
