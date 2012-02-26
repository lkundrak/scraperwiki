
from south.db import db
from django.db import models
from codewiki.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'CodeCommitEvent'
        db.create_table('codewiki_codecommitevent', (
            ('id', orm['codewiki.CodeCommitEvent:id']),
            ('revision', orm['codewiki.CodeCommitEvent:revision']),
        ))
        db.send_create_signal('codewiki', ['CodeCommitEvent'])
        
        # Adding model 'View'
        db.create_table('codewiki_view', (
            ('code_ptr', orm['codewiki.View:code_ptr']),
            ('mime_type', orm['codewiki.View:mime_type']),
        ))
        db.send_create_signal('codewiki', ['View'])
        
        # Adding model 'ScraperMetadata'
        db.create_table('codewiki_scrapermetadata', (
            ('id', orm['codewiki.ScraperMetadata:id']),
            ('name', orm['codewiki.ScraperMetadata:name']),
            ('scraper', orm['codewiki.ScraperMetadata:scraper']),
            ('run_id', orm['codewiki.ScraperMetadata:run_id']),
            ('value', orm['codewiki.ScraperMetadata:value']),
        ))
        db.send_create_signal('codewiki', ['ScraperMetadata'])
        
        # Adding model 'ScraperRunEvent'
        db.create_table('codewiki_scraperrunevent', (
            ('id', orm['codewiki.ScraperRunEvent:id']),
            ('scraper', orm['codewiki.ScraperRunEvent:scraper']),
            ('run_id', orm['codewiki.ScraperRunEvent:run_id']),
            ('pid', orm['codewiki.ScraperRunEvent:pid']),
            ('run_started', orm['codewiki.ScraperRunEvent:run_started']),
            ('run_ended', orm['codewiki.ScraperRunEvent:run_ended']),
            ('records_produced', orm['codewiki.ScraperRunEvent:records_produced']),
            ('pages_scraped', orm['codewiki.ScraperRunEvent:pages_scraped']),
            ('output', orm['codewiki.ScraperRunEvent:output']),
        ))
        db.send_create_signal('codewiki', ['ScraperRunEvent'])
        
        # Adding model 'UserCodeRole'
        db.create_table('codewiki_usercoderole', (
            ('id', orm['codewiki.UserCodeRole:id']),
            ('user', orm['codewiki.UserCodeRole:user']),
            ('code', orm['codewiki.UserCodeRole:code']),
            ('role', orm['codewiki.UserCodeRole:role']),
        ))
        db.send_create_signal('codewiki', ['UserCodeRole'])
        
        # Adding model 'UserCodeEditing'
        db.create_table('codewiki_usercodeediting', (
            ('id', orm['codewiki.UserCodeEditing:id']),
            ('user', orm['codewiki.UserCodeEditing:user']),
            ('code', orm['codewiki.UserCodeEditing:code']),
            ('editingsince', orm['codewiki.UserCodeEditing:editingsince']),
            ('runningsince', orm['codewiki.UserCodeEditing:runningsince']),
            ('closedsince', orm['codewiki.UserCodeEditing:closedsince']),
            ('twisterclientnumber', orm['codewiki.UserCodeEditing:twisterclientnumber']),
            ('twisterscraperpriority', orm['codewiki.UserCodeEditing:twisterscraperpriority']),
        ))
        db.send_create_signal('codewiki', ['UserCodeEditing'])
        
        # Adding model 'Code'
        db.create_table('codewiki_code', (
            ('id', orm['codewiki.Code:id']),
            ('title', orm['codewiki.Code:title']),
            ('short_name', orm['codewiki.Code:short_name']),
            ('source', orm['codewiki.Code:source']),
            ('description', orm['codewiki.Code:description']),
            ('created_at', orm['codewiki.Code:created_at']),
            ('deleted', orm['codewiki.Code:deleted']),
            ('status', orm['codewiki.Code:status']),
            ('guid', orm['codewiki.Code:guid']),
            ('published', orm['codewiki.Code:published']),
            ('first_published_at', orm['codewiki.Code:first_published_at']),
            ('line_count', orm['codewiki.Code:line_count']),
            ('featured', orm['codewiki.Code:featured']),
            ('istutorial', orm['codewiki.Code:istutorial']),
            ('isstartup', orm['codewiki.Code:isstartup']),
            ('language', orm['codewiki.Code:language']),
            ('wiki_type', orm['codewiki.Code:wiki_type']),
        ))
        db.send_create_signal('codewiki', ['Code'])
        
        # Adding model 'Scraper'
        db.create_table('codewiki_scraper', (
            ('code_ptr', orm['codewiki.Scraper:code_ptr']),
            ('has_geo', orm['codewiki.Scraper:has_geo']),
            ('has_temporal', orm['codewiki.Scraper:has_temporal']),
            ('last_run', orm['codewiki.Scraper:last_run']),
            ('license', orm['codewiki.Scraper:license']),
            ('license_link', orm['codewiki.Scraper:license_link']),
            ('record_count', orm['codewiki.Scraper:record_count']),
            ('scraper_sparkline_csv', orm['codewiki.Scraper:scraper_sparkline_csv']),
            ('run_interval', orm['codewiki.Scraper:run_interval']),
        ))
        db.send_create_signal('codewiki', ['Scraper'])
        
        # Adding ManyToManyField 'Code.relations'
        db.create_table('codewiki_code_relations', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_code', models.ForeignKey(orm.Code, null=False)),
            ('to_code', models.ForeignKey(orm.Code, null=False))
        ))
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'CodeCommitEvent'
        db.delete_table('codewiki_codecommitevent')
        
        # Deleting model 'View'
        db.delete_table('codewiki_view')
        
        # Deleting model 'ScraperMetadata'
        db.delete_table('codewiki_scrapermetadata')
        
        # Deleting model 'ScraperRunEvent'
        db.delete_table('codewiki_scraperrunevent')
        
        # Deleting model 'UserCodeRole'
        db.delete_table('codewiki_usercoderole')
        
        # Deleting model 'UserCodeEditing'
        db.delete_table('codewiki_usercodeediting')
        
        # Deleting model 'Code'
        db.delete_table('codewiki_code')
        
        # Deleting model 'Scraper'
        db.delete_table('codewiki_scraper')
        
        # Dropping ManyToManyField 'Code.relations'
        db.delete_table('codewiki_code_relations')
        
    
    
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
            'relations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['codewiki.Code']"}),
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
            'run_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'run_started': ('django.db.models.fields.DateTimeField', [], {}),
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
