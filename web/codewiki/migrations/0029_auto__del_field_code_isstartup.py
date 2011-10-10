# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Code.isstartup'
        db.delete_column('codewiki_code', 'isstartup')


    def backwards(self, orm):
        
        # Adding field 'Code.isstartup'
        db.add_column('codewiki_code', 'isstartup', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


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
        'codewiki.code': {
            'Meta': {'object_name': 'Code'},
            'access_apikey': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'first_published_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'forked_from': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Code']", 'null': 'True', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'istutorial': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'python'", 'max_length': '32'}),
            'line_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'privacy_status': ('django.db.models.fields.CharField', [], {'default': "'public'", 'max_length': '32'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'relations': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'relations_rel_+'", 'blank': 'True', 'to': "orm['codewiki.Code']"}),
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'ok'", 'max_length': '10', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "'Untitled'", 'max_length': '100'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'through': "orm['codewiki.UserCodeRole']", 'symmetrical': 'False'}),
            'vault': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'code_objects'", 'null': 'True', 'to': "orm['codewiki.Vault']"}),
            'wiki_type': ('django.db.models.fields.CharField', [], {'default': "'scraper'", 'max_length': '32'})
        },
        'codewiki.codepermission': {
            'Meta': {'object_name': 'CodePermission'},
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'can_write': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'code': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'permissions'", 'to': "orm['codewiki.Code']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permitted_object': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'permitted'", 'to': "orm['codewiki.Code']"})
        },
        'codewiki.codesetting': {
            'Meta': {'object_name': 'CodeSetting'},
            'code': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'settings'", 'to': "orm['codewiki.Code']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'last_edit_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_edited': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'codewiki.domainscrape': {
            'Meta': {'object_name': 'DomainScrape'},
            'bytes_scraped': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pages_scraped': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'scraper_run_event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.ScraperRunEvent']"})
        },
        'codewiki.scraper': {
            'Meta': {'object_name': 'Scraper', '_ormbases': ['codewiki.Code']},
            'code_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['codewiki.Code']", 'unique': 'True', 'primary_key': 'True'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'default': "'Unknown'", 'max_length': '100', 'blank': 'True'}),
            'license_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'run_interval': ('django.db.models.fields.IntegerField', [], {'default': '-1'})
        },
        'codewiki.scraperrunevent': {
            'Meta': {'object_name': 'ScraperRunEvent'},
            'exception_message': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'first_url_scraped': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {}),
            'pages_scraped': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pid': ('django.db.models.fields.IntegerField', [], {}),
            'records_produced': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'run_ended': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'run_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'run_started': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'scraper': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Scraper']"})
        },
        'codewiki.usercoderole': {
            'Meta': {'object_name': 'UserCodeRole'},
            'code': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Code']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'codewiki.useruserrole': {
            'Meta': {'object_name': 'UserUserRole'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'other': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rev_useruserrole_set'", 'to': "orm['auth.User']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'useruserrole_set'", 'to': "orm['auth.User']"})
        },
        'codewiki.vault': {
            'Meta': {'object_name': 'Vault'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'vault_membership'", 'symmetrical': 'False', 'to': "orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vaults'", 'to': "orm['auth.User']"})
        },
        'codewiki.view': {
            'Meta': {'object_name': 'View', '_ormbases': ['codewiki.Code']},
            'code_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['codewiki.Code']", 'unique': 'True', 'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'render_time': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['codewiki']
