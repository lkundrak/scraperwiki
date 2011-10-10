
from south.db import db
from django.db import models
from codewiki.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Changing field 'ScraperRunEvent.run_id'
        # (to signature: django.db.models.fields.CharField(max_length=100, db_index=True))
        db.alter_column('codewiki_scraperrunevent', 'run_id', orm['codewiki.scraperrunevent:run_id'])
        
        # Changing field 'ScraperRunEvent.run_started'
        # (to signature: django.db.models.fields.DateTimeField(db_index=True))
        db.alter_column('codewiki_scraperrunevent', 'run_started', orm['codewiki.scraperrunevent:run_started'])
        
    
    
    def backwards(self, orm):
        
        # Changing field 'ScraperRunEvent.run_id'
        # (to signature: django.db.models.fields.CharField(max_length=100))
        db.alter_column('codewiki_scraperrunevent', 'run_id', orm['codewiki.scraperrunevent:run_id'])
        
        # Changing field 'ScraperRunEvent.run_started'
        # (to signature: django.db.models.fields.DateTimeField())
        db.alter_column('codewiki_scraperrunevent', 'run_started', orm['codewiki.scraperrunevent:run_started'])
        
    
    
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
        'codewiki.code': {
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'first_published_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isstartup': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'istutorial': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "'Python'", 'max_length': '32'}),
            'line_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'relations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['codewiki.Code']", 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "'Untitled'", 'max_length': '100'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']"}),
            'wiki_type': ('django.db.models.fields.CharField', [], {'default': "'scraper'", 'max_length': '32'})
        },
        'codewiki.codecommitevent': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'revision': ('django.db.models.fields.IntegerField', [], {})
        },
        'codewiki.scraper': {
            'code_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['codewiki.Code']", 'unique': 'True', 'primary_key': 'True'}),
            'has_geo': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'has_temporal': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_run': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'license': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'license_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'record_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'run_interval': ('django.db.models.fields.IntegerField', [], {'default': '86400'}),
            'scraper_sparkline_csv': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'codewiki.scrapermetadata': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'run_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'scraper': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Scraper']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'codewiki.scraperrunevent': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {}),
            'pages_scraped': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'pid': ('django.db.models.fields.IntegerField', [], {}),
            'records_produced': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'run_ended': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'run_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'run_started': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'scraper': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Scraper']"})
        },
        'codewiki.usercodeediting': {
            'closedsince': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Code']", 'null': 'True'}),
            'editingsince': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'runningsince': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'twisterclientnumber': ('django.db.models.fields.IntegerField', [], {'unique': 'True'}),
            'twisterscraperpriority': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'codewiki.usercoderole': {
            'code': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['codewiki.Code']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'codewiki.view': {
            'code_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['codewiki.Code']", 'unique': 'True', 'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }
    
    complete_apps = ['codewiki']