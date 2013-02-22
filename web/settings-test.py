from settings import *

# Ways of speeding up tests.
# See: http://stackoverflow.com/questions/3096148/how-to-run-djangos-test-database-only-in-memory
DATABASES['default']['ENGINE'] = 'sqlite3'
#DATABASES['default']['NAME'] = 'test-database.db'
#DATABASES['default']['TEST_NAME'] = ':memory:'
DATABASES['default']['NAME'] = '/tmp/test-database.db'

# Any options specified are going to be MySQL specific.
del(DATABASES['default']['OPTIONS'])
SOUTH_TESTS_MIGRATE = False
OVERDUE_SQL = "julianday(strftime(?,last_run) + run_interval,'unixepoch') < julianday('now', 'localtime') or last_run is null"
OVERDUE_SQL_PARAMS = ['%s']
LETTUCE_TESTING = True

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/sw_lettuce_terrain_emails'
