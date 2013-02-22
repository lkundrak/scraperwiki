
from django.forms.fields import MultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple

from django.conf import settings
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django import forms
from frontend.models import UserProfile, DataEnquiry,Feature
from contact_form.forms import ContactForm
from registration.forms import RegistrationForm
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from captcha.fields import CaptchaField
from codewiki.models import SCHEDULE_OPTIONS, Scraper, Code

from email.Utils import parseaddr, formataddr

#from django.forms.extras.widgets import Textarea
class SearchForm(forms.Form):
    q = forms.CharField(label='Find datasets', max_length=50)
    

# see also is_emailer in the Code model
def get_emailer_for_user(user):
    try:
        queryset = Scraper.objects.exclude(privacy_status="deleted")
        queryset = queryset.filter(Q(usercoderole__role='owner') & Q(usercoderole__user=user))
        queryset = queryset.filter(Q(usercoderole__role='email') & Q(usercoderole__user=user))
        return queryset.latest('id')
    except:
        return None

    
class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

        self.user = self.instance.user
        self.emailer = get_emailer_for_user(self.user)

        if self.emailer:
            self.fields['alert_frequency'].initial = self.emailer.run_interval
        else:
            # fallback on once a day while not all users have an emailer
            self.fields['alert_frequency'].initial = 86400

        self.fields['email'].initial = self.user.email
        
    email_intervals = []
    for s in SCHEDULE_OPTIONS:
        email_intervals.append([s[0], s[1]])

    alert_frequency = forms.ChoiceField(required=False, 
                                        label="How often do you want to be emailed?", 
                                        choices = email_intervals)
    bio = forms.CharField(label="A bit about you", widget=forms.Textarea(), required=False)
    email = forms.EmailField(label="Email Address")
    messages = forms.BooleanField(required=False, 
                                        label="Would you like to be able to send and receive messages through ScraperWiki?", )
    features = forms.ModelMultipleChoiceField(required=False,
                        widget=CheckboxSelectMultiple, queryset=Feature.objects.filter(public=True))
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if email != self.user.email and User.objects.filter(email__iexact=email).count() > 0:
            raise forms.ValidationError("This email address is already used by another account.")

        return email

    class Meta:
        model = UserProfile
        fields = ('bio', 'name', 'messages', 'features')

    def save(self, *args, **kwargs):
        self.user.email = self.cleaned_data['email']
        self.user.save()

        if self.emailer:
            self.emailer.run_interval = self.cleaned_data['alert_frequency']
            self.emailer.save()

        return super(UserProfileForm, self).save(*args,**kwargs)

class ScraperWikiContactForm(ContactForm):
    def __init__(self, data=None, files=None, request=None, *args, **kwargs):
        super(ScraperWikiContactForm, self).__init__(data=data, files=files, request=request, *args, **kwargs)
        if not request.user.is_authenticated():
            self.fields['captcha'] = CaptchaField()
        
    subject_dropdown = forms.ChoiceField(label="Subject type", choices=(('suggestion', 'Suggestion about how we can improve something'),('request', 'I want you to scrape some data for me'),('premium','I have a question about Premium Accounts'),('corporate',"I'd like to talk to you about a Corporate Account"),('help', 'I need help using ScraperWiki'), ('bug', 'I want to report a bug'), ('other', 'Other')))
    title = forms.CharField(widget=forms.TextInput(), label=u'Subject')
    recipient_list = [settings.FEEDBACK_EMAIL]

    def from_email(self):
        return formataddr((self.cleaned_data['name'], self.cleaned_data['email']))


class UserMessageForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea, label=_(u'Message'))
    
class SigninForm(forms.Form):
    user_or_email = forms.CharField(label=_(u'Username or email'))
    password = forms.CharField(label=_(u'Password'), widget=forms.PasswordInput())
    remember_me = forms.BooleanField(widget=forms.CheckboxInput(),
                           label=_(u'Remember me'), required=False)

    def clean(self):
        cleaned_data = self.cleaned_data

        user = authenticate(username=cleaned_data.get('user_or_email', ''), password=cleaned_data.get('password', ''))
        if user is None:
            raise forms.ValidationError("Sorry, but we could not find that user, or the password was wrong")
        elif not user.is_active:
            raise forms.ValidationError(mark_safe("This account has not been activated (ScraperWiki will have allowed you to use the site before activation for your first time). Please check your email (including the spam folder) and click on the link to confirm your account. If you have lost the email or the link has expired please <a href='%s'>request a new one</a>." % reverse('resend_activation_email')))

        return cleaned_data


class CreateAccountForm(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service and makes sure the email address is unique.

    """
    name = forms.CharField()
    tos = forms.BooleanField(widget=forms.CheckboxInput(),
                           label=_(u'I agree to the ScraperWiki terms and conditions'),
                           error_messages={ 'required': _("You must agree to the ScraperWiki terms and conditions") })

    def clean_email(self):
       """
       Validate that the supplied email address is unique for the
       site.

       """
       if User.objects.filter(email__iexact=self.cleaned_data['email']):
           raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
       return self.cleaned_data['email']

class ResendActivationEmailForm(forms.Form):
    email_address = forms.EmailField()

class DataEnquiryForm(forms.ModelForm):
    name = forms.CharField(required=True, label='Your Name:', error_messages={'required':'Please tell us your name.'})
    email = forms.CharField(required=True, label='Your Email address:', error_messages={'required':'Please tell us your email.'})
    phone = forms.CharField(required=True, label='Your Phone or Skype:', error_messages={'required':'How can we contact you?'})
    description = forms.CharField(required=False, widget=forms.Textarea, label='Project brief: (optional)')
    ip = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = DataEnquiry
