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

from frontend import highrise


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
    user             = models.ForeignKey(User, unique=True)
    name             = models.CharField(max_length=64)
    bio              = models.TextField(blank=True, null=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    beta_user        = models.BooleanField( default=False )
    apikey           = models.CharField(max_length=64, null=True, blank=True)
    
    objects = models.Manager()
    
    def regenerate_apikey(self):
        import uuid
        self.apikey = str( uuid.uuid4() )
    

    def save(self):
        #this seems pretty pointless
        new = False
        if not self.pk:
            new = True
        
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
            First Name: %s
            Last Name: %s
            Your email address: %s
            Your telephone number: %s
            Your company name: %s
            At which URL(s) can we find the data currently?: %s
            What information do you want scraped?: %s
            When do you need it by?: %s
            How often does the data need to be scraped?: %s
            What are your ETL needs?: %s
            What visualisation do you need?: %s
            What application do you want built?: %s
        """ % (self.category,
               self.first_name,
               self.last_name,
               self.email,
               self.telephone,
               self.company_name,
               self.urls,
               self.columns,
               self.due_date or '',
               self.frequency,
               self.description,
               self.visualisation,
               self.application)

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
