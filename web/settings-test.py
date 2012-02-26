from settings import *

DATABASES['default']['NAME'] = 'test-database.db'
DATABASES['default']['ENGINE'] = 'sqlite3'
# Any options specified are going to be MySQL specific.
del DATABASES['default']['OPTIONS']
SOUTH_TESTS_MIGRATE = False
OVERDUE_SQL = "julianday(strftime(?,last_run) + run_interval,'unixepoch') < julianday('now', 'localtime') or last_run is null"
OVERDUE_SQL_PARAMS = ['%s']
LETTUCE_TESTING = True

