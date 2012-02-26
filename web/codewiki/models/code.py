import datetime
import time
import os, sys
import re
import urllib

from django.template import RequestContext
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db.models import Q
from django.contrib.comments.signals import comment_was_posted
from django.core.mail import send_mail
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse                

import tagging
import hashlib

from codewiki import vc
from codewiki import util
from codewiki.models.vault import Vault
from frontend.models import UserProfile
import textile   # yuk
import creoleparser  # creoleparser.text2html(cdesc); method may include pre and post processing of text to handle links and paramstrings encoding nicely

try:
    import json
except:
    import simplejson as json

LANGUAGES_DICT = {
    'python' : 'Python',
    'php' : 'PHP',
    'ruby' : 'Ruby',

    'html' : 'HTML',
    'javascript' : 'Javascript',
    #'css' : 'CSS',
    #'wikicreole' : 'Wikicreole',
}
LANGUAGES = [ (k,v) for k,v in LANGUAGES_DICT.iteritems() ]

# used for new scraper/view dialogs
# Add "javascript" to enable Javascript
SCRAPER_LANGUAGES = [ (k, LANGUAGES_DICT[k]) for  k in ["python", "ruby", "php" ] ]
SCRAPER_LANGUAGES_V = [ '2.7.1', '1.9.2', '5.3.5', ''] 

VIEW_LANGUAGES = [ (k, LANGUAGES_DICT[k]) for  k in ["python", "ruby", "php", "html"] ]
HELP_LANGUAGES = [ (k, LANGUAGES_DICT[k]) for  k in ["python", "ruby", "php"] ]

WIKI_TYPES = (
    ('scraper', 'Scraper'),
    ('view', 'View'),    
)

PRIVACY_STATUSES = (
    ('public', 'Public'),
    ('visible', 'Visible'),
    ('private', 'Private'),
    ('deleted', 'Deleted'),
)

STAFF_ACTIONS = set(["run_scraper"])
CREATOR_ACTIONS = set(["delete_data", "undo_delete_data","schedule_scraper", "delete_scraper", "killrunning", "set_privacy_status", "schedulescraper", "set_controleditors" ])
EDITOR_ACTIONS = set(["changeadmin", "savecode", "settags", "stimulate_run", "remove_self_editor", "change_attachables", "attachable_add", "getrawdescription"])
STAFF_EXTRA_ACTIONS = CREATOR_ACTIONS | EDITOR_ACTIONS - set(['savecode']) # let staff also do anything a creator / editor can, except save code is a bit rude (for now!)
VISIBLE_ACTIONS = set(["rpcexecute", "readcode", "readcodeineditor", "overview", "history", "comments", "exportsqlite", "setfollow" ])

MAGIC_RUN_INTERVAL = 1000000000

def scraper_search_query_unordered(user, query, apikey=None):
    if query:
        scrapers = Code.objects.filter(title__icontains=query)
        scrapers_description = Code.objects.filter(description__icontains=query)
        scrapers_slug = Code.objects.filter(short_name__icontains=query)
        scrapers_all = scrapers | scrapers_description | scrapers_slug
    else:
        scrapers_all = Code.objects
    scrapers_all = scrapers_all.exclude(privacy_status="deleted")
    
    u = user
    if apikey:
        # If we have an API key then we should look up the userprofile and 
        # use that user instead of the one supplied
        try:
            u = UserProfile.objects.get(apikey=apikey).user
        except UserProfile.DoesNotExist:
            u = None
    
    if u and not u.is_anonymous():
        scrapers_all = scrapers_all.exclude(Q(privacy_status="private") & ~(Q(usercoderole__user=u) & Q(usercoderole__role='owner')) & ~(Q(usercoderole__user=u) & Q(usercoderole__role='editor')))
    else:
        scrapers_all = scrapers_all.exclude(privacy_status="private")
    return scrapers_all
        
def scraper_search_query(user, query, apikey=None):
    scrapers_all = scraper_search_query_unordered(user, query, apikey=None)
    scrapers_all = scrapers_all.order_by('-created_at')
    return scrapers_all.distinct()

def user_search_query(user, query, apikey=None):
    users_name = User.objects.filter(userprofile__name__icontains=query)
    users_bio = User.objects.filter(userprofile__bio__icontains=query)
    users_username = User.objects.filter(username__icontains=query)
    users_all = users_name | users_bio | users_username
    users_all.order_by('-created_at')
    return users_all.distinct()


class Code(models.Model):

    # model fields
    title              = models.CharField(max_length=100,
                                        null=False,
                                        blank=False,
                                        verbose_name='Scraper Title',
                                        default='Untitled')
    short_name         = models.CharField(max_length=50, unique=True)
    description        = models.TextField(blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    status             = models.CharField(max_length=10, blank=True, default='ok')   # "sick", "ok"
    users              = models.ManyToManyField(User, through='UserCodeRole')
    guid               = models.CharField(max_length=1000)
    line_count         = models.IntegerField(default=0)    
    featured           = models.BooleanField(default=False)
    istutorial         = models.BooleanField(default=False)
    language           = models.CharField(max_length=32, choices=LANGUAGES,  default='python')
    wiki_type          = models.CharField(max_length=32, choices=WIKI_TYPES, default='scraper')    
    relations          = models.ManyToManyField("self", blank=True)  # manage.py refuses to generate the tabel for this, so you haev to do it manually.
    forked_from        = models.ForeignKey('self', null=True, blank=True)
    privacy_status     = models.CharField(max_length=32, choices=PRIVACY_STATUSES, default='public')
    previous_privacy   = models.CharField(max_length=32, choices=PRIVACY_STATUSES, null=True, blank=True)
    has_screen_shot    = models.BooleanField( default=False )
    
    # For private scrapers this can be provided to API calls as proof that the caller has access
    # to the scraper, it is really a shared secret between us and the caller. For the datastore 
    # API call it will only be used to verify access to the main DB, not the attached as that is 
    # done through the existing code permissions model.  
    # This should be regeneratable on demand by any editor/owner of the scraper (if it is private)
    access_apikey = models.CharField(max_length=64, blank=True, null=True)
    
    # Each code object can be contained in a vault, and a reference to that vault is maintained
    # here
    vault = models.ForeignKey( Vault, related_name='code_objects', null=True, blank=True, on_delete=models.SET_NULL )

    def __init__(self, *args, **kwargs):
        super(Code, self).__init__(*args, **kwargs)
        if not self.created_at:
            self.created_at = datetime.datetime.today()  

    def save(self, *args, **kwargs):
        # Check type and apikey and generate one if necessary
        if self.privacy_status == "private" and not self.access_apikey:
            self.generate_apikey()

        if not self.short_name:
            self._buildfromfirsttitle()

        if not self.guid:
            self.set_guid()

        super(Code, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return self.short_name

    @property
    def vcs(self):
        return vc.MercurialInterface(self.get_repo_path())

    def commit_code(self, code_text, commit_message, user):
        self.vcs.savecode(code_text, "code")
        rev = self.vcs.commit(message=commit_message, user=user)
        return rev

    def set_docs(self, description, user):
        self.description = description
        self.vcs.savecode(description, "docs")
        rev = self.vcs.commit(message="save docs", user=user)

    def generate_apikey(self):
        import uuid
        self.access_apikey = str( uuid.uuid4() )

    def get_commit_log(self, filename):
        return self.vcs.getcommitlog(filename)

    def get_file_status(self):
        return self.vcs.getfilestatus("code")

    # this is hardcoded to get revision list for "code"
    def get_vcs_status(self, revision = None):
        return self.vcs.getstatus(revision)

    def get_reversion(self, rev):
        return self.vcs.getreversion(rev)

    def _buildfromfirsttitle(self):
        assert not self.short_name
        self.short_name = util.SlugifyUniquely(self.title, Code, slugfield='short_name', instance=self)
        assert self.short_name != ''

    def last_runevent(self):
        lscraperrunevents = self.scraper.scraperrunevent_set.all().order_by("-run_started")[:1]
        return lscraperrunevents and lscraperrunevents[0] or None

    def is_sick_and_not_running(self):
        lastscraperrunevent = self.last_runevent()
        if self.status == 'sick':
            if (not lastscraperrunevent) or (not lastscraperrunevent.id) or (lastscraperrunevent.id and lastscraperrunevent.pid == -1):
                return True
        return False

    def set_guid(self):
        self.guid = hashlib.md5("%s" % ("**@@@".join([self.short_name, str(time.mktime(self.created_at.timetuple()))]))).hexdigest()
     
        
        # it would be handy to get rid of this function
    def owner(self):
        if self.pk:
            owner = self.users.filter(usercoderole__role='owner')
            if len(owner) >= 1:
                return owner[0]
        return None


    def editors(self):
        if self.pk:
            return self.users.filter(usercoderole__role='editor')
        return None

    def attachable_scraperdatabases(self):
        return [ cp.permitted_object  for cp in CodePermission.objects.filter(code=self).all()  if cp.permitted_object.privacy_status != "deleted" ]

    # could filter for the private scrapers which this user is allowed to see!
    def attachfrom_scrapers(self):
        return [ cp.code  for cp in CodePermission.objects.filter(permitted_object=self).all()  if cp.permitted_object.privacy_status not in ["deleted", "private"] ]
        

    def add_user_role(self, user, role='owner'):
        """
        Method to add a user as either an editor or an owner to a scraper/view.
  
        - `user`: a django.contrib.auth.User object
        - `role`: String, either 'owner' or 'editor'
        
        Valid role are:
          * "owner"
          * "editor"
          * "follow"
          * "requester"
          * "email"
        
        """

        valid_roles = ['owner', 'editor', 'follow', 'requester', 'email']
        if role not in valid_roles:
            raise ValueError("""
              %s is not a valid role.  Valid roles are:\n
              %s
              """ % (role, ", ".join(valid_roles)))

        #check if role exists before adding 
        u, created = UserCodeRole.objects.get_or_create(user=user, 
                                                           code=self, 
                                                           role=role)

    # should eventually replace add_user_role
    # knows what roles are redundant to each other
    def set_user_role(self, user, role, remove=False):
        assert role in ['owner', 'editor', 'follow']  # for now
        userroles = UserCodeRole.objects.filter(code=self, user=user)
        euserrole = None
        for userrole in userroles:
            if userrole.role == role:
                if remove:
                    userrole.delete()
                else:
                    euserrole = userrole
            elif userrole.role in ['owner', 'editor', 'follow'] and role in ['owner', 'editor', 'follow']:
                userrole.delete()
        
        if not euserrole and not remove:
            euserrole = UserCodeRole(code=self, user=user, role=role)
            euserrole.save()
        return euserrole
        
    
    # uses lists of users rather than userroles so that you can test containment easily
    def userrolemap(self):
        result = { "editor":[], "owner":[]}
        for usercoderole in self.usercoderole_set.all():
            if usercoderole.role not in result:
                result[usercoderole.role] = [ ]
            result[usercoderole.role].append(usercoderole.user)
        return result
    


    def saved_code(self, revision = None):
        return self.get_vcs_status(revision)["code"]

    def get_repo_path(self):
        if settings.SPLITSCRAPERS_DIR:
            return os.path.join(settings.SPLITSCRAPERS_DIR, self.short_name)
        # XXX this should either raise an error, or return something, in the case
        # where SPLITSCRAPERS_DIR isn't set. no idea if there is some real case
        # where that happens

    def get_absolute_url(self):
        from django.contrib.sites.models import Site
        from django.core.urlresolvers import reverse        
        
        current_site = Site.objects.get_current()
        r = reverse('code_overview', kwargs={'wiki_type':self.wiki_type, 'short_name':self.short_name})
        url = 'https://%s%s' % (current_site.domain,r,)
        return url


    # update scraper meta data (lines of code etc)    
    def update_meta(self):
        pass

    # this is just to handle the general pointer put into Alerts
    def content_type(self):
        return ContentType.objects.get(app_label="codewiki", model="Code")

    def get_screenshot_filename(self, size='medium'):
        return "%s.png" % self.short_name

    def get_screenshot_filepath(self, size='medium'):
        filename = self.get_screenshot_filename(size)
        return os.path.join(settings.SCREENSHOT_DIR, size, filename)

    def screenshot_url(self, size='medium'):
        from django.conf import settings        
        
        if self.has_screenshot(size):
            url = settings.MEDIA_URL + 'screenshots/' + size + '/' + self.get_screenshot_filename(size=size)
        else:
            url = settings.MEDIA_URL + 'images/testcard_' + size + '.png'
        return url
        
    def has_screenshot(self, size='medium'):
        has =  os.path.exists(self.get_screenshot_filepath(size))
        if has and not self.has_screen_shot:
            self.has_screen_shot = True
            self.save()
        return has

    class Meta:
        app_label = 'codewiki'

    # the only remaining reference to textile
    def description_ashtml(self):
        cdesc = self.description_safepart()
        if re.search("__BEGIN", self.description):
            envvars = self.description_envvars()
            nqsenvvars = len(re.findall("=", envvars.get("QUERY_STRING", "")))
            if nqsenvvars:
                cdesc = "%s\n\n_Has %d secret query-string environment variable%s._" % (cdesc, nqsenvvars, (nqsenvvars>1 and "s" or ""))

        # Doing some very crude XSS protection
        cdesc = re.sub("<(\s*script)(?i)", "&lt;\\1", cdesc)
        if not re.search("<", cdesc):
            text = textile.textile(cdesc)   # wikicreole at the very least here!!!
            text = text.replace("&#8220;", '"')
            text = text.replace("&#8221;", '"')
            text = text.replace("&#8217;", "'")
        else:
            text = cdesc
        return text

        

    def description_safepart(self):   # used in the api output
        cdesc = re.sub('(?s)__BEGIN_QSENVVARS__.*?__END_QSENVVARS__', '', self.description)
        cdesc = re.sub('(?s)__BEGIN_ENVVARS__.*?__END_ENVVARS__', '', cdesc)
        return cdesc 
        
    # You can encode the query string as individual elements, or as one block.  
    # If controller/node can drop in environment variables directly, then we can consider a general purpose adding of 
    # such environment variables not through the QUERY_STRING interface which requires decoding in the scraper.
    # Would be more traditional to obtain the values as os.getenv("TWITTER_API_KEY") than dict(cgi.parse_qsl(os.getenv("QUERY_STRING")))["TWITTER_API_KEY"]
    def description_envvars(self):
        qsenvvars = { }
        for lines in re.findall('(?s)__BEGIN_QSENVVARS__(.*?)__END_QSENVVARS__', self.description):
            for line in lines.split("\n"):
                sline = line.strip()
                if sline:
                    psline = sline.partition("=")
                    qsenvvars[psline[0].strip()] = psline[2].strip()
        envvars = { }
        if qsenvvars:
            envvars["QUERY_STRING"] = urllib.urlencode(qsenvvars)
        for lines in re.findall('(?s)__BEGIN_ENVVARS__(.*?)__END_ENVVARS__', self.description):
            for line in lines.split("\n"):
                sline = line.strip()
                if sline:
                    psline = sline.partition("=")
                    envvars[psline[0].strip()] = line[2].strip()
        return envvars




    # all authorization to go through here
    def actionauthorized(self, user, action):
        if user and not user.is_anonymous():
            roles = [ usercoderole.role  for usercoderole in UserCodeRole.objects.filter(code=self, user=user) ]
        else:
            roles = [ ]
        #print "Code.actionauthorized AUTH", (action, user, roles, self.privacy_status)
        
        # roles are: "owner", "editor", "follow", "requester", "email"
        # privacy_status: "public", "visible", "private", "deleted"
        if self.privacy_status == "deleted":
            return False
            
        # extra type control condition
        if action == "rpcexecute" and self.wiki_type != "view":
            return False
        
        if action in STAFF_ACTIONS:
            return user.is_staff
            
        if user.is_staff and action in STAFF_EXTRA_ACTIONS:  
            return True
        
        if action in CREATOR_ACTIONS:
            return "owner" in roles
        
        if action in EDITOR_ACTIONS:
            if self.privacy_status == "public":
                return user.is_authenticated()
                
            return "editor" in roles or "owner" in roles
        
        if action in VISIBLE_ACTIONS:
            if self.privacy_status == "private":
                return "editor" in roles or "owner" in roles
            return True
                
        assert False, ("unknown action", action)
        return True

    def authorizationfailedmessage(self, user, action):
        if self.privacy_status == "deleted":
            return {'heading': 'Deleted', 'body': "Sorry this %s has been deleted" % self.wiki_type}
        if action == "rpcexecute" and self.wiki_type != "view":
            return {'heading': 'This is a scraper', 'body': "Not supposed to run a scraper as a view"}
        if action in STAFF_ACTIONS:
            return {'heading': 'Not authorized', 'body': "Only staff can do action %s" % action}
        if action in CREATOR_ACTIONS:
            return {'heading': 'Not authorized', 'body': "Only owner can do action %s" % action}
        if action in EDITOR_ACTIONS:
            if self.privacy_status != "public":
                return {'heading': 'Not authorized', 'body': "This %s can only be edited by its owner and designated editors" % self.wiki_type}
            if not user.is_authenticated():
                return {'heading': 'Not authorized', 'body': "Only logged in users can edit things"}
        if action in VISIBLE_ACTIONS:
            if self.privacy_status == "private":
                return {'heading': 'Not authorized', 'body': "Sorry, this %s is private" % self.wiki_type}
        return {'heading': "unknown", "body":"unknown"}

    def api_actionauthorized(self, apikey):
        if self.privacy_status == 'private':
            return all([ self.access_apikey, apikey, self.access_apikey == apikey ])
        return True

    
    # tags have been unhelpfully attached to the scraper and view classes rather than the base code class
    # we can minimize the damage caused by this decision (in terms of forcing the scraper/view code to be 
    # unnecessarily separate by filtering as much of this application as possible through this interface
    def gettags(self):
        if self.wiki_type == "scraper":
            return tagging.models.Tag.objects.get_for_object(self.scraper)
        return tagging.models.Tag.objects.get_for_object(self.view)

    def settags(self, tag_names):
        if self.wiki_type == "scraper":
            tagging.models.Tag.objects.update_tags(self.scraper, tag_names)
        else:
            tagging.models.Tag.objects.update_tags(self.view, tag_names)

    # is the automatically made, builtin emailer
    def is_emailer(self):
        return self.short_name[-8:] == '.emailer'


# I think this is another of those things that could be saved into the mercurial docs field 
# (as a query_string itself) so we can use the history and editing permissions all there.
# would considerably simplify the situation
class CodeSetting(models.Model):
    """
    A single key=value setting for a scraper/view that is editable for that
    view/scraper by the owner (or editor). There will be several (potentially)
    of these per scraper/view that are only visible to owners and editors where 
    the scraper/view is private/protected.
    
    It is passed through the system with the code when executed and so will
    be available within the scraper code via an internal api setting - such
    as scraperwiki.setting('name')

    
    Records the user who last saved the setting (and when) so that there is 
    a minimal amount of auditing available.  
    """
    code  = models.ForeignKey(Code, related_name='settings')
    key   = models.CharField(max_length=100)
    value = models.TextField()
    last_edited = models.ForeignKey(User)
    last_edit_date = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return repr(self)

    def __repr__(self):
        return '<CodeSetting: %s for %s>' % (self.key, self.code.short_name,)

    class Meta:
        app_label = 'codewiki'


class CodePermission(models.Model):
    """
    A uni-directional permission to read/write to a particular scraper/view
    for another scraper/view.
    """
    code = models.ForeignKey(Code, related_name='permissions')    
    permitted_object = models.ForeignKey(Code, related_name='permitted')    # should call this permitted_code so we don't assume is untyped
    
    def __unicode__(self):
        return u'%s CANATTACHTO %s' % (self.code.short_name, self.permitted_object.short_name,)

    class Meta:
        app_label = 'codewiki'
    

class UserCodeRole(models.Model):
    user    = models.ForeignKey(User)
    code    = models.ForeignKey(Code)
    role    = models.CharField(max_length=100)   # ['owner', 'editor', 'follow', 'requester', 'email']

    def __unicode__(self):
        return "Scraper_id: %s -> User: %s (%s)" % (self.code, self.user, self.role)

    class Meta:
        app_label = 'codewiki'


class UserUserRole(models.Model):
    pass



def comment_notification(**kwargs):
    """
    Allows us to notify the owner of the scraper should another user comment 
    on it.  Disabled until we can agree on the format of the email.
    """
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    
    request = kwargs.pop('request')
    comment = kwargs.pop('comment')
    
    scraper = comment.content_object
    owner = scraper.owner()    
    message = comment.comment
    subject = "New comment on '%s'" % scraper.title

    if request.user == owner:
        return
        
    site = Site.objects.get_current()
    sender_profile_url = "https://%s%s" % (site.domain,reverse("profiles_profile_detail",kwargs={"username":request.user.username}))
        
    if owner.get_profile().email_on_comments: 
        text_content = render_to_string('emails/new_comment.txt', locals(), context_instance=RequestContext(request) )
        html_content = render_to_string('emails/new_comment.html', locals(),context_instance=RequestContext(request) )
        
        msg = EmailMultiAlternatives(subject, text_content, settings.FEEDBACK_EMAIL, [owner.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)

comment_was_posted.connect(comment_notification)
