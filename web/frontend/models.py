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
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag, calculate_cloud, get_tag_list, LOGARITHMIC, get_queryset_and_model
from tagging.models import Tag, TaggedItem

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
        return ('profile', (), { 'username': self.user.username })
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
    
    # sorts against what the current user can see and what the identity of the profiled_user
    def owned_code_objects(self, user):
        from codewiki.models import scraper_search_query
        return scraper_search_query(user, None).filter(usercoderole__user=self.user)

    def emailer_code_objects(self, username, user):
        return self.owned_code_objects(user).filter(Q(usercoderole__user__username=username) & Q(usercoderole__role='email'))

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

class Tags:

    @classmethod
    def sorted(self):
        from codewiki.models import Scraper
        #popular tags
        #this is a horrible hack, need to patch http://github.com/memespring/django-tagging to do it properly
        tags_sorted = sorted([(tag, int(tag.count)) for tag in Tag.objects.usage_for_model(Scraper, counts=True)], key=lambda k:k[1], reverse=True)[:40]
        tags = []
        for tag in tags_sorted:
            # email (for emailers) and test far outweigh other tags :(
            if tag[0].name not in ['test','email']:
                tags.append(tag[0])
        return tags

class DataEnquiry(models.Model):
    date_of_enquiry = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=64)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True)
    description = models.TextField()
    ip = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        verbose_name_plural = "data enquiries"

    def __unicode__(self):
        return u"%s %s <%s>" % (self.first_name, self.last_name, self.email)

def data_enquiry_post_save(sender, **kwargs):
    if kwargs['created']:
        instance = kwargs['instance']

        subject = "Data request [ID %s] from %s" % (instance.id, instance.name)

        text_content = render_to_string('emails/request_data.txt', locals())
        html_content = render_to_string('emails/request_data.html', locals())

        msg = EmailMultiAlternatives(subject, text_content, instance.email, [settings.FEEDBACK_EMAIL])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)


post_save.connect(data_enquiry_post_save, sender=DataEnquiry)





