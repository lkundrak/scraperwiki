from django.conf import settings
from django.utils.html import escape
import django.db as db
import re


from django.contrib.sites.models import Site, RequestSite
from django.utils.safestring import mark_safe
from frontend.models import Message
import settings
import datetime

# Enable proper linebreaks in the SQL
enable_linebreaks_regex = re.compile(",(?! )")
def enable_linebreaks(str):
    return enable_linebreaks_regex.sub(",<wbr>", str)

def vault_info(request):
    """
    Sets vault info for the current user if it exists, ideally we could cache
    this somewhere.
    """
    from codewiki.models import Vault
    
    # TODO: Cache vault info for user
    if not request.user.is_authenticated():
        return {}
        
    try:
        v = request.user.vaults
    except Vault.DoesNotExist:
        return {}
        
    # Accessing the request.user.vaults should be done in the specific template
    # where it is used rather than in every request
    return { 'uservaults': v }
    

# Taken from http://www.djangosnippets.org/snippets/1197/
def site(request):
    """
    Grabs the 'site' app's information, and makes it availile to templates
    """
    site_info = {'protocol': request.is_secure() and 'https' or 'http'}
    if Site._meta.installed:
        site_info['domain'] = Site.objects.get_current().domain
    else:
        site_info['domain'] = RequestSite(request).domain
    return site_info
    

def template_settings(request):
    """
    Looks for a list in settings (and therefore any varible imported in to the
    global namespace in settings, such as 'localsettings') called 
    'TEMPLATE_SETTINGS'.
    
    If the list exists, it will be assumes that each item in the list is the 
    name of a defined setting.  This setting (key and value) is then appended
    to a dict, that is returned in to the RequestContext for use in templates.
    
    Care should be taken not to add any database or other 'private' settings
    in to the list, as potentially it will be visable in templates.
    """
    
    settings_dict = settings.__dict__
    availible_settings = settings_dict.get('TEMPLATE_SETTINGS', [])
    template_settings = {}
    for setting in availible_settings:
        if setting in settings_dict:
            template_settings[setting] = settings_dict[setting]
            
    return {'settings' : template_settings}

# not used since design revamp in April 2011, commented out in global_settings.py too
# def site_messages(request):
#    message = Message.objects.get_active_message(datetime.datetime.now())
#    return {'site_message': mark_safe(message.text)}

#################################################################################
# SQL Debug code

# wraps around a query dict as provided by django, to output the sql part per 
# default if accessed without an index.
class SqlQuery(object):
    def __init__(self, query):
        self.query = query
    def __getitem__(self, k):
        return self.query[k]
    # per default, return the sql query
    def __str__(self):
        return enable_linebreaks(escape(self['sql']))

# provides sqldebug.queries
class SqlQueries(object):
    def __iter__(self):
        for q in db.connection.queries:
            yield SqlQuery(q)

    def __len__(self):
        return len(db.connection.queries)
        
    def count(self):
        return len(self)
    
    # per default, output as list of LI elements
    def __str__(self):        
        result = ""
        for q in self:
            result += "<li>" + escape(q["sql"]) + "</li>\n"
        return result            

# main class for sql debugging info
class SqlDebug(object):
    def __init__(self):
        # allow access to database queries via attribute
        self.queries = SqlQueries()
        
    # per default, display some basic information
    def __str__(self):
        return "%d queries, %f seconds" % (self.queries.count(), self.time())
        
    # checks whether sql debugging has been enabled
    def enabled(self):        
        ena = getattr(settings, 'SQL_DEBUG', False) and \
               getattr(settings, 'DEBUG', False)
        return ena
        
    # shortcurt to enabled()
    def __nonzero__(self):
        return self.enabled()
        
    # returns aggregate time for db operations as a double
    def time(self):
        secs = 0.0
        for s in self.queries:
            secs += float(s['time'])
        return secs

# context processor function: makes a SqlDebug instance available to templates.
def sqldebug(request):
    return {'sqldebug': SqlDebug()}
