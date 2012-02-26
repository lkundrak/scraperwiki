import datetime

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.dispatch import dispatcher
from django.core.mail import send_mail, mail_admins
from django.conf import settings
from django.core.exceptions import PermissionDenied

from frontend import highrise

class Feature(models.Model):
    """
    These models are used to denote whether a user has access to a specific
    feature, i.e. whether they turned it off or not. Those features that do
    not have the public flag set will not be visible on the user profile page.
    """
    name = models.CharField(max_length=32)
    description = models.TextField(blank=True, null=True)
    public = models.BooleanField( default=True )

    class Meta(object):
        ordering = ['name']

    def __unicode__(self):
        return self.name


class UserProfile(models.Model):
    """
    This model holds the additional fields to be associated with a user in the
    system
    
    Note, where any other model wishes to link to a user or reference a user,
    they should link to the user profile (this class), rather than directly to
    the user. this ensures that if we wish to change the definition of user,
    we only have to alter the UserProfile class to have everything continue to
    work instead of refactoring every place that connects to a resource/class
    outside of this application.
    """
    plan_choices = choices=(('free', 'Free'),
               ('individual', 'Individual'),
               ('business', 'Business'),
               ('corporate', 'Corporate'),
              )
    user             = models.ForeignKey(User, unique=True)
    name             = models.CharField(max_length=64)
    bio              = models.TextField(blank=True, null=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    beta_user        = models.BooleanField( default=False )
    apikey           = models.CharField(max_length=64, null=True, blank=True)
    # The user's payment plan.
    plan             = models.CharField(max_length=64,
      choices=plan_choices, default='free')
    
    features         = models.ManyToManyField( "Feature", related_name='features', null=True, blank=True )
    
    # If someone comments on an item this user owns, this specifies whether they 
    # should receive the email
    email_on_comments = models.BooleanField( default=False )
    messages = models.BooleanField( default=False )
        
    objects = models.Manager()
    
    def has_feature(self, fname):
        """ 
            Returns true if this profile has a feature connected with 
            the specified name 
            Use it something like this: request.user.get_profile().has_feature('xxx')
        """
        return self.features.filter(name=fname).count() > 0
    
    def possible_feature_count(self):
        return Feature.objects.filter(public=True).count()
    
    def regenerate_apikey(self):
        import uuid
        self.apikey = str( uuid.uuid4() )

    def save(self):
        if not self.apikey:
            self.regenerate_apikey()
        
        #do the parent save
        super(UserProfile, self).save()

    def display_name(self):
        if self.name and self.name != '':
            return self.name
        return self.user.username
    
    def __unicode__(self):
        return unicode(self.user)

    class Meta:
        ordering = ('-created_at',)
    
    def get_absolute_url(self):
        return ('profiles_profile_detail', (), { 'username': self.user.username })
    get_absolute_url = models.permalink(get_absolute_url)        

    def change_plan(self, plan):
        """Change the user's payment plan.  For example, upgrading them when
        they have submitted a successful credit card subscription.
        """

        valid_choices = dict(self.plan_choices).keys()
        if plan not in valid_choices:
            raise ValueError("The plan %r is invalid (%r are acceptable)" %
              (plan, valid_choices))

        self.plan = plan
        self.save()
    
    def create_vault(self, name):
        """Create a Vault.  Checks that the user is authorised to do so;
        raises an Exception if not.
        """

        from codewiki.models import Vault

        valid_for_vault = dict(self.plan_choices).keys()
        valid_for_vault.remove('free')

        if self.plan not in valid_for_vault:
            raise PermissionDenied
        vault = Vault(user=self.user, name=name, plan=self.plan)
        vault.save()
        vault.members.add(self.user)
        return vault

# Signal Registrations
# when a user is created, we want to generate a profile for them

def create_user_profile(sender, instance, created, **kwargs):
    if created and sender == User:
        try:
            profile = UserProfile(user=instance)
            profile.save()
        except:
            # syncdb is saving the superuser
            # UserProfile is yet to be created by migrations
            pass

models.signals.post_save.connect(create_user_profile)

class MessageManager(models.Manager):
    def get_active_message(self, now):
        """
        The active message is the one that is displayed on the site.

        It is the most recently created message that isn't excluded
        because of its start or finish date.
        """
        messages = self.filter(Q(start__isnull=True) | Q(start__lte=now))
        messages = messages.filter(Q(finish__isnull=True) | Q(finish__gte=now))
        return messages.latest('id')


class Message(models.Model):
    text = models.TextField()
    start = models.DateTimeField(blank=True, null=True)
    finish = models.DateTimeField(blank=True, null=True)
    objects = MessageManager()

    def is_active_message(self):
        return Message.objects.get_active_message(datetime.datetime.now()) == self

    def __unicode__(self):
        if self.is_active_message():
            return "%s [Active]" % self.text
        else:
            return "%s [Inactive]" % self.text


class DataEnquiry(models.Model):
    date_of_enquiry = models.DateTimeField(auto_now_add=True)
    urls = models.TextField()
    columns = models.TextField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    email = models.EmailField()
    telephone = models.CharField(max_length=32, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    visualisation = models.TextField(null=True, blank=True)
    application = models.TextField(null=True, blank=True)
    company_name = models.CharField(max_length=128, null=True, blank=True)
    broadcast = models.BooleanField()
    why = models.TextField(null=True, blank=True)

    FREQUENCY_CHOICES = (
      ('once', 'Once only'),
      ('monthly', 'Monthly'),
      ('weekly', 'Weekly'),
      ('daily', 'Daily'),
      ('hourly', 'Hourly'),
      ('realtime', 'Real-time')
    )
    frequency = models.CharField(max_length=32, choices=FREQUENCY_CHOICES)

    CATEGORY_CHOICES = (
        ('private', 'private'),
        ('viz', 'viz'),
        ('app', 'app'),
        ('etl', 'etl'),
        ('public', 'public')
    )
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)

    class Meta:
        verbose_name_plural = "data enquiries"

    def __unicode__(self):
        return u"%s %s <%s>" % (self.first_name, self.last_name, self.email)

    def email_message(self):
        msg =  u"""
            Category: %s
            -----
            Name: %s %s
            Email address: %s
            Telephone number: %s
            Company name: %s
            -----
            At which URL(s) can we find the data currently?
            > %s
            
            What information do you want scraped?
            > %s
            
            When do you need it by?
            > %s
            
            How often does the data need to be scraped?
            > %s
            
            What are your ETL needs?
            > %s
            
            What visualisation do you need?
            > %s
            
            What application do you want built?
            > %s
            
            Why do you want to liberate this data?
            > %s
            
            Are you happy for this to be broadcasted on Twitter/Facebook?
            > %s
            
        """ % (self.category,
               self.first_name,
               self.last_name,
               self.email,
               self.telephone or '(not specified)',
               self.company_name or '(not specified)',
               self.urls or '(not specified)',
               self.columns or '(not specified)',
               self.due_date or '(none)',
               self.frequency or '(not specified)',
               self.description or '(not specified)',
               self.visualisation or '(not specified)',
               self.application or '(not specified)',
               self.why or '(not specified)',
               self.broadcast or '(not specified)')

        return msg.encode('utf-8')

def data_enquiry_post_save(sender, **kwargs):
    if kwargs['created']:
        instance = kwargs['instance']
        send_mail('Data Request', instance.email_message(), instance.email, [settings.FEEDBACK_EMAIL], fail_silently=False)

        if not hasattr(settings,'HIGHRISE_ENABLED') or settings.HIGHRISE_ENABLED == False:
            return

        if instance.category not in ['public']:
            try:
                h = highrise.HighRise(settings.HIGHRISE_PROJECT, settings.HIGHRISE_KEY)

                try:
                    requester = h.search_people_by_email(instance.email.encode('utf-8'))[0]
                except Exception,err:
                    # Removed indexerror to catch problems that seem to happen when we 
                    # can't find the user.                    
                    try:
                        requester = h.create_person(instance.first_name.encode('utf-8'),
                                                    instance.last_name.encode('utf-8'),
                                                    instance.email)
                        h.tag_person(requester.id, 'Lead')
                    except Exception, e2:
                        mail_admins('HighRise failed to find/create user with errors', str(err) + ',' + str(e2))                    
                        return

                h.create_note_for_person(instance.email_message(), requester.id)

                cat = h.get_task_category_by_name('To Do')

                task_owner = h.get_user_by_email(settings.HIGHRISE_ASSIGN_TASK_TO)

                # Split out so we can tell which one is causing the problems
                rid = requester.id
                cid = cat.id
                tid = task_owner.id
                
                h.create_task_for_person('Data Request Followup', tid, cid, rid)
            except highrise.HighRiseException, ex:
                msg = "%s\n\n%s" % (ex.message, instance.email_message())
                mail_admins('HighRise update failed', msg)
            except AttributeError, eAttr:
                # We expect this from create_task_for_person with missing data.
                msg = "%s\n\n%s" % (str(eAttr), instance.email_message())
                mail_admins('HighRise update failed', msg)
            

post_save.connect(data_enquiry_post_save, sender=DataEnquiry)
