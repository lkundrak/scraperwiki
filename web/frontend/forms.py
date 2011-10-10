from django.conf import settings
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django import forms
from frontend.models import UserProfile, DataEnquiry
from contact_form.forms import ContactForm
from registration.forms import RegistrationForm
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from captcha.fields import CaptchaField
from codewiki.models import SCHEDULE_OPTIONS, Scraper, Code


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

    alert_frequency = forms.ChoiceField(required=False, 
                                        label="How often do you want to be emailed?", 
                                        choices = SCHEDULE_OPTIONS)
    bio = forms.CharField(label="A bit about you", widget=forms.Textarea(), required=False)
    email = forms.EmailField(label="Email Address")
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if email != self.user.email and User.objects.filter(email__iexact=email).count() > 0:
            raise forms.ValidationError("This email address is already used by another account.")

        return email

    class Meta:
        model = UserProfile
        fields = ('bio', 'name')

    def save(self, *args, **kwargs):
        self.user.email = self.cleaned_data['email']
        self.user.save()

        if self.emailer:
            self.emailer.run_interval = self.cleaned_data['alert_frequency']
            self.emailer.save()

        return super(UserProfileForm, self).save(*args,**kwargs)

class scraperContactForm(ContactForm):
    def __init__(self, data=None, files=None, request=None, *args, **kwargs):
        super(scraperContactForm, self).__init__(data=data, files=files, request=request, *args, **kwargs)
        if not request.user.is_authenticated():
            self.fields['captcha'] = CaptchaField()
        
    subject_dropdown = forms.ChoiceField(label="Subject type", choices=(('suggestion', 'Suggestion about how we can improve something'),('request', 'Request data'),('help', 'Help using ScraperWiki'), ('bug', 'Report a bug'), ('other', 'Other')))
    title = forms.CharField(widget=forms.TextInput(), label=u'Subject')
    recipient_list = [settings.FEEDBACK_EMAIL]

    def from_email(self):
        return self.cleaned_data['email']


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
    def __init__(self, *args, **kwargs):
        super(DataEnquiryForm, self).__init__(*args, **kwargs)
        self.fields['frequency'].initial = 'daily'

    urls = forms.CharField(required=False, label='At which URL(s) can we find the data currently?')
    columns = forms.CharField(required=False, widget=forms.Textarea, label='What information do you want scraped?')
    due_date = forms.DateField(required=False, label='When do you need it by?')
    first_name = forms.CharField(label='First name:')
    last_name = forms.CharField(label='Last name:')
    email = forms.CharField(label='Your email address:')
    telephone = forms.CharField(required=False, label='Your telephone number:')
    company_name = forms.CharField(required=False, label='Your company name:')
    broadcast = forms.BooleanField(initial=True, required=False, label='I\'m happy for this request to be posted on Twitter/Facebook')
    description = forms.CharField(required=False, widget=forms.Textarea, label='What are your ETL needs?')
    visualisation = forms.CharField(required=False, widget=forms.Textarea, label='What visualisation do you need?')
    application = forms.CharField(required=False, widget=forms.Textarea, label='What application do you want built?')
    frequency = forms.ChoiceField(label='How often does the data need to be scraped?', choices=DataEnquiry.FREQUENCY_CHOICES)

    def clean(self):
        cleaned_data = self.cleaned_data

        if not cleaned_data.get('first_name') or not cleaned_data.get('last_name') or not cleaned_data.get('email'):
            raise forms.ValidationError("So we can get back to you, please fill in your name and email.")

        if cleaned_data['category'] == 'public' and cleaned_data['broadcast'] == False:
            raise forms.ValidationError("Sorry, we can only help with free public data requests if you're happy for us to post it on social networks.")

        return cleaned_data

    class Meta:
        model = DataEnquiry