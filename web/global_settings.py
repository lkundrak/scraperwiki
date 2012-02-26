"""
Global settings file.

Everything in here is imported *before* everything in settings.py.

This means that this file is used for default, fixed and global varibles, and
then settings.py is used to overwrite anything here as well as adding settings
particular to the install.

Note that there are no tuples here, as they are immutable. Please use lists, so
that in settings.py we can do list.append()
"""
import os
from os.path import exists, join

# This shouldn't be needed, however in some cases the buildout version of
# django (in bin/django) may not make the paths correctly
import sys
sys.path.append('web')

# Django settings for scraperwiki project.

DEBUG = True

TIME_ZONE = 'Europe/London'
LANGUAGE_CODE = 'en_GB'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
HOME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # the parent directory of SCRAPERWIKI_DIR
SCRAPERWIKI_DIR     = HOME_DIR + '/web/'
MEDIA_DIR = SCRAPERWIKI_DIR + 'media'
MEDIA_URL = 'http://media.scraperwiki.com/'
MEDIA_ADMIN_DIR = SCRAPERWIKI_DIR + '/media-admin'
LOGIN_URL = '/login/'
HOME_DIR = ""

# MySQL default overdue scraper query
OVERDUE_SQL = "(DATE_ADD(last_run, INTERVAL run_interval SECOND) < NOW() or last_run is null)"
OVERDUE_SQL_PARAMS = []

# URL that handles the media served from MEDIA_ROOT. Make sure to use a trailing slash.
URL_ROOT = ""
MEDIA_ROOT = URL_ROOT + 'media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a trailing slash.
ADMIN_MEDIA_PREFIX = URL_ROOT + '/media-admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'x*#sb54li2y_+b-ibgyl!lnd^*#=bzv7bj_ypr2jvon9mwii@z'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = [
    'middleware.exception_logging.ExceptionLoggingMiddleware',
    'middleware.improved_gzip.ImprovedGZipMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_notify.middleware.NotificationsMiddleware',
    'pagination.middleware.PaginationMiddleware',    
    'middleware.csrfcookie.CsrfAlwaysSetCookieMiddleware',
    'api.middleware.CORSMiddleware'
]

AUTHENTICATION_BACKENDS = [
    'frontend.email_auth.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend'
]

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = [
    join(SCRAPERWIKI_DIR, 'templates'),
]

TEMPLATE_CONTEXT_PROCESSORS = [
  'django.contrib.auth.context_processors.auth', 
  'django.core.context_processors.debug',
  'django.core.context_processors.i18n',
  'django.core.context_processors.media',
  'django.core.context_processors.request',
  'django.contrib.messages.context_processors.messages',
  'django_notify.context_processors.notifications',
  'frontend.context_processors.site',
  'frontend.context_processors.template_settings',
  'frontend.context_processors.vault_info',  
  # 'frontend.context_processors.site_messages', # disabled as not used since design revamp April 2011
]

SCRAPERWIKI_APPS = [
    # the following are scraperwiki apps
    'frontend',
    'codewiki',
    'api',
    'cropper',
    'kpi',
    'documentation',
    #'devserver',
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.markup',
    'registration',
    'south',
    'profiles',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django_notify',
    'tagging',
    'contact_form',
    'captcha',
    'pagination',    
    'compressor',
] + SCRAPERWIKI_APPS

TEST_RUNNER = 'scraperwiki_tests.run_tests' 

ACCOUNT_ACTIVATION_DAYS = 3650 # If you haven't activated in 10 years then tough luck!

# tell Django that the frontent user_profile model is to be attached to the
# user model in the admin side.
AUTH_PROFILE_MODULE = 'frontend.UserProfile'

INTERNAL_IPS = ['127.0.0.1',]


NOTIFICATIONS_STORAGE = 'session.SessionStorage'
REGISTRATION_BACKEND = "frontend.backends.UserWithNameBackend"

#tagging
FORCE_LOWERCASE_TAGS = True


# define default directories needed for paths to run scrapers
SCRAPER_LIBS_DIR = join(HOME_DIR, "scraperlibs")

#send broken link emails
SEND_BROKEN_LINK_EMAILS = DEBUG == False

#pagingation
SCRAPERS_PER_PAGE = 50

#API
MAX_API_ITEMS = 500
DEFAULT_API_ITEMS = 100

# Make "view on site" work for user models
# https://docs.djangoproject.com/en/dev/ref/settings/?#absolute-url-overrides
ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda o: o.get_profile().get_absolute_url()
}

# Required for the template_settings context processor. Each varible listed
# here will be made availible in all templates that are passed the
# RequestContext.  Be careful of listing database and other private settings 
# here
TEMPLATE_SETTINGS = [
 'API_URL',
 'ORBITED_URL',
 'MAX_DATA_POINTS',
 'MAX_MAP_POINTS',
 'REVISION',
 'VIEW_URL',
 'CODEMIRROR_URL'
]

try:
    REVISION = open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'revision.txt')).read()[:-1]
except:
    REVISION = ""

MAX_DATA_POINTS = 500

BLOG_FEED = 'http://blog.scraperwiki.com/feed/atom'

DATA_TABLE_ROWS = 10
RSS_ITEMS = 50

VIEW_SCREENSHOT_SIZES = {'small': (110, 73), 'medium': (220, 145), 'large': (800, 600)}
SCRAPER_SCREENSHOT_SIZES = {'small': (110, 73), 'medium': (220, 145) }

CODEMIRROR_VERSION = "0.94"
CODEMIRROR_URL = "CodeMirror-%s/" % CODEMIRROR_VERSION

APPROXLENOUTPUTLIMIT = 3000

CONFIGFILE = "/var/www/scraperwiki/uml/uml.cfg"

HTTPPROXYURL = "http://localhost:9005"
DISPATCHERURL = "http://localhost:9000"

PAGINATION_DEFAULT_PAGINATION=20

# tell south to do migrations when doing tests
SOUTH_TESTS_MIGRATE = True

# To be overridden in actual settings files
SESSION_COOKIE_SECURE = False

# Enable logging of errors to text file, taken from:
# http://stackoverflow.com/questions/238081/how-do-you-log-server-errors-on-django-sites
import logging
from middleware import exception_logging
logging.custom_handlers = exception_logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format' : '%(asctime)s %(name)s %(filename)s:%(lineno)s %(levelname)s: %(message)s'
        }
    },
    'handlers': {
        # Include the default Django email handler for errors
        # This is what you'd get without configuring logging at all.
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
             # But the emails are plain text by default - HTML is nicer
            'include_html': True,
        },
        # Log to a text file that can be rotated by logrotate
        'logfile': {
            'class': 'logging.custom_handlers.WorldWriteRotatingFileHandler',
            'filename': '/var/log/scraperwiki/django-www.log',
            'mode': 'a',
            'maxBytes': 100000,
            'backupCount': 5,
            'formatter': 'simple'
        },
    },
    'loggers': {
        # Again, default Django configuration to email unhandled exceptions
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # Might as well log any errors anywhere else in Django 
        # (so use empty string for name here to catch anything)
        '': {
            'handlers': ['logfile'],
            'level': DEBUG and 'DEBUG' or 'ERROR',
            'propagate': False,
        },
        # Your own app - this assumes all your logger names start with "myapp."
        #'myapp': {
        #    'handlers': ['logfile'],
        #    'level': 'WARNING', # Or maybe INFO or DEBUG
        #    'propagate': False
        #},
    },
}


# Javascript templating
INSTALLED_APPS += ['icanhaz']
ICANHAZ_DIRS = [SCRAPERWIKI_DIR + 'templates/codewiki/js/']

