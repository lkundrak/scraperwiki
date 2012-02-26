from django import forms
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response, redirect
from django.contrib import auth
from django.shortcuts import get_object_or_404
from django.conf import settings
from frontend.forms import SigninForm, UserProfileForm, SearchForm, ResendActivationEmailForm, DataEnquiryForm
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
# https://docs.djangoproject.com/en/dev/ref/contrib/csrf/
from django.views.decorators.csrf import csrf_exempt

from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag, calculate_cloud, get_tag_list, LOGARITHMIC, get_queryset_and_model
from tagging.models import Tag, TaggedItem

from codewiki.models import Code, UserCodeRole, Scraper, Vault, View, scraper_search_query, user_search_query, HELP_LANGUAGES, LANGUAGES_DICT
from django.db.models import Q
from frontend.forms import CreateAccountForm, UserMessageForm
from registration.backends import get_backend
from frontend.models import UserProfile
from codewiki.models import Scraper
        
# find this in lib/python/site-packages/profiles
from profiles import views as profile_views   

import django.contrib.auth.views
import os
import re
import datetime
import urllib
import itertools
import json
import recurly
recurly.js.PRIVATE_KEY = settings.RECURLY_PRIVATE_KEY

from utilities import location


def frontpage(request, public_profile_field=None):
    user = request.user

    #featured
    featured_both = Code.objects.filter(featured=True).exclude(privacy_status="deleted").exclude(privacy_status="private").order_by('-created_at')[:4]
	
    #popular tags
    #this is a horrible hack, need to patch http://github.com/memespring/django-tagging to do it properly
    tags_sorted = sorted([(tag, int(tag.count)) for tag in Tag.objects.usage_for_model(Scraper, counts=True)], key=lambda k:k[1], reverse=True)[:40]
    tags = []
    for tag in tags_sorted:
        # email (for emailers) and test far outweigh other tags :(
        if tag[0].name not in ['test','email']:
            tags.append(tag[0])
    
    data = {
			'featured_both': featured_both,
            'tags': tags, 
            'language': 'python'}
    return render_to_response('frontend/frontpage.html', data, context_instance=RequestContext(request))

@login_required
def dashboard(request, privacy_status=None, page_number=1):
    user = request.user
    owned_or_edited_code_objects = scraper_search_query(request.user, None).filter(usercoderole__user=user)
    
    if privacy_status == 'private':
        owned_or_edited_code_objects = owned_or_edited_code_objects.filter(privacy_status="private")
    elif privacy_status == 'nonprivate':
        owned_or_edited_code_objects = owned_or_edited_code_objects.filter(Q(privacy_status="public")|Q(privacy_status="visible"))
    
    context = {'object_list': owned_or_edited_code_objects,
               'language':'python' }
    return render_to_response('frontend/dashboard.html', context, context_instance = RequestContext(request))


def profile_detail(request, username):
    # The templates for this view are in templates/profiles/
    user = request.user
    profiled_user = get_object_or_404(User, username=username)
    
    # sorts against what the current user can see and what the identity of the profiled_user
    extra_context = { }
    owned_code_objects = scraper_search_query(request.user, None).filter(usercoderole__user=profiled_user)
    extra_context['owned_code_objects'] = owned_code_objects
    extra_context['emailer_code_objects'] = owned_code_objects.filter(Q(usercoderole__user__username=username) & Q(usercoderole__role='email'))
    return profile_views.profile_detail(request, username=username, extra_context=extra_context)


def user_message(request, username):
    """
        This is a view to return a form ready for the user to send an 
        email message to another user on the site.
    """
    form = UserMessageForm(data=request.POST or None)
    receiving_user = get_object_or_404(User, username=username)
    if request.method == "POST" and form.is_valid():
        #  send email
        from django.template.loader import render_to_string
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives

        sending_user_profile = get_object_or_404(UserProfile, user=request.user)
        receiving_user_profile = get_object_or_404(UserProfile, user=receiving_user)
        
        subject = "New message from %s" % sending_user_profile.display_name()
        body = form.cleaned_data['body']

        site = Site.objects.get_current()
        reply_url = "https://%s%s#message" % (site.domain,reverse("profiles_profile_detail",kwargs={"username":sending_user_profile.user.username}))
        sender_profile_url = "https://%s%s" % (site.domain,reverse("profiles_profile_detail",kwargs={"username":sending_user_profile.user.username}))
        if sending_user_profile.messages and receiving_user_profile.messages:
            text_content = render_to_string('emails/new_message.txt', locals(), context_instance=RequestContext(request) )
            html_content = render_to_string('emails/new_message.html', locals(), context_instance=RequestContext(request) )
        
            msg = EmailMultiAlternatives(subject, text_content, settings.FEEDBACK_EMAIL, [receiving_user_profile.user.email])
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
        else:
            return HttpResponse('{"status" : "fail", "error" : "Both you and the recipient must allow messages"}')
            
        return HttpResponse('{"status" : "ok"}')
        
    elif request.method == "POST":
        return HttpResponse('{"status" : "fail", "error" : "Please fill in the message"}')
        
    return render_to_response('profiles/message.html', {'form':form, 'profile' : receiving_user}, context_instance = RequestContext(request))

def edit_profile(request):
    form = UserProfileForm()
    return profile_views.edit_profile(request, form_class=form)

def process_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('frontpage'))

def login(request):
    error_messages = []

    #grab the redirect URL if set
    redirect = request.GET.get('next') or request.POST.get('redirect', '')

    #Create login and registration forms
    login_form = SigninForm()
    registration_form = CreateAccountForm()
    
    if request.method == 'POST':
        #Existing user is logging in
        if request.POST.has_key('login'):

            login_form = SigninForm(data=request.POST)
            if login_form.is_valid():
                user = auth.authenticate(username=request.POST['user_or_email'], password=request.POST['password'])

                #Log in
                auth.login(request, user)

                #set session timeout
                if request.POST.has_key('remember_me'):
                    request.session.set_expiry(settings.SESSION_TIMEOUT)

                if redirect:
                    return HttpResponseRedirect(redirect)
                else:
                    return HttpResponseRedirect(reverse('frontpage'))

        #New user is registering
        elif request.POST.has_key('register'):

            registration_form = CreateAccountForm(data=request.POST)

            if registration_form.is_valid():
                backend = get_backend(settings.REGISTRATION_BACKEND)             
                new_user = backend.register(request, **registration_form.cleaned_data)

                #sign straight in
                signed_in_user = auth.authenticate(username=request.POST['username'], password=request.POST['password1'])
                auth.login(request, signed_in_user)                

                #redirect
                if redirect:
                    return HttpResponseRedirect(redirect)
                else:
                    return HttpResponseRedirect(reverse('frontpage'))

    return render_to_response('registration/extended_login.html', {'registration_form': registration_form,
                                                                   'login_form': login_form, 
                                                                   'error_messages': error_messages,  
                                                                   'redirect': redirect}, context_instance = RequestContext(request))

def help(request, mode=None, language=None):
    tutorials = {}
    viewtutorials = {}
    if not language:
        language = "python"
    display_language = LANGUAGES_DICT[language]
    other_languages = [ (l, d) for (l, d) in HELP_LANGUAGES if l != language]
    
    if mode=="code_documentation": # Support legacy URL. 
        mode="documentation"
    
    context = { 'mode' : mode, 'language' : language, 'display_language' : display_language, 
             'tutorials': tutorials, 'viewtutorials': viewtutorials, 
             'other_languages' : other_languages }
    
    if not mode or mode=="intro":
        mode = "intro"
        context["include_tag"] = "frontend/help_intro.html"
        context["mode"] = "intro"
    elif mode=="faq":
        mode = "faq"
        context["include_tag"] = "frontend/help_faq.html"
        context["mode"] = "faq"
    elif mode=="tutorials":
        # new ordering by the number at start of title, which we then strip out for display
        if language == "python":
            tutorials[language] = Scraper.objects.filter(privacy_status="public", istutorial=True, language=language).order_by('title')
            for scraper in tutorials[language]:
                scraper.title = re.sub("^[\d ]+", "", scraper.title)
        else:
            tutorials[language] = Scraper.objects.filter(privacy_status="public", istutorial=True, language=language).order_by('created_at')
        viewtutorials[language] = View.objects.filter(privacy_status="public", istutorial=True, language=language).order_by('created_at')
        context["include_tag"] = "frontend/help_tutorials.html"
    
    else: 
        context["include_tag"] = "frontend/help_%s_%s.html" % (mode, language)
    
    return render_to_response('frontend/help.html', context, context_instance = RequestContext(request))

def browse_wiki_type(request, wiki_type=None, page_number=1):
    special_filter = request.GET.get('filter', None)
    ff = request.GET.get('forked_from', None)
    return browse(request, page_number, wiki_type, special_filter,ff)

def browse(request, page_number=1, wiki_type=None, special_filter=None, ff=None):
    all_code_objects = scraper_search_query(request.user, None).select_related('owner','owner__userprofile_set')

    if wiki_type:
        all_code_objects = all_code_objects.filter(wiki_type=wiki_type) 

    # One last check because this is a slightly convoluted way of building this page.
    if not ff:
        ff = request.GET.get('forked_from', None)
        
    if ff:
        try:
            s = Scraper.objects.get(short_name=ff)
            if s and not s.privacy_status == 'private' and not s.privacy_status == 'deleted':
                all_code_objects = all_code_objects.filter(forked_from=s)
        except Scraper.DoesNotExist:
            # Just ignore the forked_from if the scraper does not exist
            pass

    #extra filters (broken scraper lists etc)
    if special_filter == 'sick':
        all_code_objects = all_code_objects.filter(status='sick')
    elif special_filter == 'no_description':
        all_code_objects = all_code_objects.filter(description='')
    elif special_filter == 'no_tags':
        #hack to get scrapers with no tags (tags don't recognise inheritance)
        if wiki_type == 'scraper':
            all_code_objects = TaggedItem.objects.get_no_tags(Scraper.objects.exclude(privacy_status="deleted").order_by('-created_at') )
        else:
            all_code_objects = TaggedItem.objects.get_no_tags(View.objects.exclude(privacy_status="deleted").order_by('-created_at') )


    # filter out scrapers that have no records unless we are looking at the forked_from list
    if not ff and not special_filter:
        all_code_objects = all_code_objects.exclude(wiki_type='scraper', scraper__record_count=0)
    
    form = SearchForm()

    dictionary = { "ff": ff, "scrapers": all_code_objects, 'wiki_type':wiki_type, "form": form, 'special_filter': special_filter, 'language': 'python'}
    return render_to_response('frontend/browse.html', dictionary, context_instance=RequestContext(request))


def search_urls(request, partial):
    """
    When we search we want to handle anything that looks like a url and search for it within the 
    codewiki.DomainScrape. This isn't mapped to a URL at the moment, it is expected that it will 
    only be called from the search view.
    
    This does not take account of private scrapers that you do have access to, instead showing
    only public and protected scrapers, for now.
    """
    from codewiki.models import DomainScrape
    from urlparse import urlparse
    from django.db.models import Q

    url = urlparse(partial)
    q = Q(scraper_run_event__scraper__privacy_status__in=['public','protected'])
    q = q & (Q(domain__istartswith='http://%s' % (url.netloc,)) | Q(domain__istartswith='https://%s' % (url.netloc,)))
    dsqs = DomainScrape.objects.filter(q).distinct('scraper_run_event__scraper')
    
    ctx = {
        'form'     : SearchForm(initial={'q': partial}),
        'scrapers_num_results'    : dsqs.count(),
        'scrapers' : [ d.scraper_run_event.scraper for d in dsqs.all().distinct() ],
    }
    
    # TODO: We need a template for url search results
    return render_to_response('frontend/search_url_results.html', ctx, context_instance = RequestContext(request))



def search(request, q=""):
    if (q != ""):
        form = SearchForm(initial={'q': q})
        q = q.strip()

        # If q looks like a url then we should just pass it through to search_urls
        # and return that instead.
        if re.match('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', q):
            return search_urls(request,q)
        
        tags = Tag.objects.filter(name__icontains=q)
        scrapers = scraper_search_query(request.user, q)
        
        # The following line used to exclude private scrapers, but these were already excluded in 
        # the call to scraper_search_query above.
        scrapers = scrapers.exclude(usercoderole__role='email') 
        scrapers_num_results = tags.count() + scrapers.count()

        users = user_search_query(request.user, q)
        users_num_results = users.count()

        return render_to_response('frontend/search_results.html',
            {
                'scrapers': scrapers,
                'users': users,
                'tags': tags,
                'scrapers_num_results': scrapers_num_results,
                'users_num_results': users_num_results,
                'form': form,
                'query': q},
            context_instance=RequestContext(request))

    # If the form has been submitted, or we have a search term in the URL
    # - redirect to nice URL
    elif (request.POST):
        form = SearchForm(request.POST)
        if form.is_valid():
            q = form.cleaned_data['q']
            # Process the data in form.cleaned_data
            # Redirect after POST
            return HttpResponseRedirect('/search/%s/' % urllib.quote(q.encode('utf-8')))
        else:
            form = SearchForm()
            return render_to_response('frontend/search_results.html', {'form': form},
                context_instance=RequestContext(request))
    else:
        form = SearchForm()
        return render_to_response('frontend/search_results.html', {'form': form}, context_instance = RequestContext(request))

def get_involved(request):

        scraper_count = Scraper.objects.exclude(privacy_status="deleted").count()
        view_count = View.objects.exclude(privacy_status="deleted").count()
        
        #no description
        scraper_no_description_count = Scraper.objects.filter(description='').exclude(privacy_status="deleted").count()
        scraper_description_percent = 100 - int(scraper_no_description_count / float(scraper_count) * 100)

        view_no_description_count = View.objects.filter(description='').exclude(privacy_status="deleted").count()
        view_description_percent = 100 - int(view_no_description_count / float(view_count) * 100)

        #no tags
        scraper_no_tags_count = TaggedItem.objects.get_no_tags(Scraper.objects.exclude(privacy_status="deleted")).count()
        scraper_tags_percent = 100 - int(scraper_no_tags_count / float(scraper_count) * 100)
    
        view_no_tags_count = TaggedItem.objects.get_no_tags(View.objects.exclude(privacy_status="deleted")).count()
        view_tags_percent = 100 - int(view_no_tags_count / float(view_count) * 100)

        #scraper status
        scraper_sick_count = Scraper.objects.filter(status='sick').exclude(privacy_status="deleted").count()
        scraper_sick_percent = 100 - int(scraper_sick_count / float(scraper_count) * 100)

        data = {
            'scraper_count': scraper_count,
            'view_count': view_count,
            'scraper_no_description_count': scraper_no_description_count,
            'scraper_description_percent': scraper_description_percent,
            'view_no_description_count': view_no_description_count,
            'view_description_percent': view_description_percent,
            'scraper_no_tags_count': scraper_no_tags_count,
            'scraper_tags_percent': scraper_tags_percent,
            'view_no_tags_count': view_no_tags_count,
            'view_tags_percent': view_tags_percent,
            'scraper_sick_count': scraper_sick_count,
            'scraper_sick_percent': scraper_sick_percent,
            'language': 'python', 
        }

        return render_to_response('frontend/get_involved.html', data, context_instance=RequestContext(request))



def events(request, e=''):
    names = ['jdcny','ltdmo','jdcdc']
    if e in names:
        url = 'frontend/events/%s.html' % e
        data = {}
    else:
        url = 'frontend/events/index.html'
        data = names
    return render_to_response(url, data, context_instance=RequestContext(request))



@login_required
def stats(request):
    return render_to_response('frontend/stats.html', {}, context_instance=RequestContext(request))
    

def tags(request):
    all_tags = {}
    
    # Want 2.7 for the collections.Counter :(
    def update_tags(tag):
        existing = all_tags.get(tag.name, None)
        if existing:
            existing.count += tag.count
        else:
            all_tags[tag.name] = tag
        
    scraper_tags = Tag.objects.usage_for_model(Scraper, counts=True, filters={'privacy_status':'public', 'privacy_status':'visible'})
    view_tags = Tag.objects.usage_for_model(View, counts=True, filters={'privacy_status':'public', 'privacy_status':'visible'})
    for tag in itertools.chain(scraper_tags, view_tags):
        update_tags(tag)
    
    # Use UserCodeRole objects to get code objects that are private but 
    # accessible to this user and then use update_tags to update the 
    # dictionary
    if request.user.is_authenticated():
        privatescraper_ids = [u.code.id for u in UserCodeRole.objects.filter(code__privacy_status='private', user=request.user)]
        qs = Code.objects.filter(pk__in=privatescraper_ids)
        extra_tags = Tag.objects.usage_for_queryset(qs, counts=True)
        for tag in extra_tags:
            update_tags(tag)
        
    tags = calculate_cloud(all_tags.values(), steps=4, distribution=LOGARITHMIC)

    return render_to_response('frontend/tags.html', {'tags':tags}, context_instance=RequestContext(request))
    
def tag(request, tag):
    ttag = get_tag(tag)
    code_objects = None
    
    if ttag:
        # query set of code objects this user can see
        user_visible_code_objects = scraper_search_query(request.user, None)

        # inlining of tagging.models.get_by_model() but removing the content_type_id condition so that tags 
        # attached to scrapers and views get interpreted as tags on code objects
        code_objects = user_visible_code_objects.extra(
            tables=['tagging_taggeditem'],
            where=['tagging_taggeditem.tag_id = %s', 'codewiki_code.id = tagging_taggeditem.object_id'], 
            params=[ttag.pk])

    return render_to_response('frontend/tag.html', {'tag_string': tag, 'tag' : ttag, 'scrapers': code_objects}, context_instance=RequestContext(request))

def resend_activation_email(request):
    form = ResendActivationEmailForm(request.POST or None)

    template = 'frontend/resend_activation_email.html'
    if form.is_valid():
        template = 'frontend/resend_activation_complete.html'
        try:
            user = User.objects.get(email=form.cleaned_data['email_address'])
            if not user.is_active:
                site = Site.objects.get_current()
                user.registrationprofile_set.get().send_activation_email(site)
        except Exception, ex:
            print ex

    return render_to_response(template, {'form': form}, context_instance = RequestContext(request))

def request_data(request):
    form = DataEnquiryForm(request.POST or None)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('request_data_thanks'))
    return render_to_response('frontend/request_data.html', {'form': form}, context_instance = RequestContext(request))

def request_data_public(request):
    return render_to_response('frontend/request_data_public.html', context_instance = RequestContext(request))

def request_data_thanks(request):
    return render_to_response('frontend/request_data_thanks.html', context_instance = RequestContext(request))

def generate_recurly_signature(plan_code, account_code):
    signature = recurly.js.sign_subscription(plan_code, account_code)
    return signature

def subscribe(request, plan):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login') + "?next=" + request.path)

    plans = { 
        'individual' : { 
            'name' : 'Individual', 
            'code' : 'individual'
        }, 
        'business' : { 
            'name' : 'Business', 
            'code' : 'business'
        }, 
        'corporate' : { 
            'name' : 'Corporate', 
            'code' : 'corporate'
        }
    }
    context = plans[plan]
    context['subdomain'] = settings.RECURLY_SUBDOMAIN
    account_code = "%s-%s" % (request.user.id, request.user.username)
    context['signature'] = generate_recurly_signature(plan_code=plan, account_code=account_code)
    context['account_code'] = account_code
    context['enable_coupons'] = False
    if request.user.get_profile().has_feature('Alpha Vault User'):
        context['enable_coupons'] = True
    return render_to_response('frontend/subscribe.html', context, context_instance = RequestContext(request))

def unpack_recurly_result(request):
    """Helper function for confirm_subscription.
    Each recurly result comes in a key of the form: "recurly_result[thing]";
    we have to unpack those into the dictionary that verify_subscription expects.
    """

    def strip_brackets(s):
        """Given a string "prefix[thing]" return "thing".
        """
        import re

        m = re.search(r'.*\[(.*)\]', s)
        return m.group(1)

    return dict((strip_brackets(k), v)
      for k,v in request.POST.items() if 'recurly_result' in k)

def user_profile_from_account_code(account_code):
    """From the account_code, created in *subscribe()* (above), extract the user id,
    and then the UserProfile object, which is returned.
    """

    id = int(account_code.split('-')[0])
    user = User.objects.get(id=id)
    return user.get_profile()

# We're CSRF exempt because we only expect recurly to POST here, and they use their own
# authentication/signing mechanism, so we know that random people will not be able
# to successfully POST.
@csrf_exempt
def confirm_subscription(request):
    """We arrive here when recurly POST to this confirmation page."""

    """
    signature
    account_code
    plan_code
    add_on_codes
    couponcode
    """

    from recurly.js import RequestForgeryError

    recurly_result = unpack_recurly_result(request)

    try:
       recurly.js.verify_subscription(recurly_result)
    except RequestForgeryError:
       # Private key is invalid or the result was tampered with.
       # Log?
       return HttpResponseForbidden('Do not call this, imp!')

    # Upgrade users account...
    profile = user_profile_from_account_code(recurly_result['account_code'])
    plan = recurly_result['plan_code']
    profile.change_plan(plan)
    # ... and create a vault if they don't already have one.
    vs = Vault.objects.filter(user=profile.user)
    if len(vs) == 0:
        profile.create_vault(name='My first vault')

    request.session['recently_upgraded'] = True

    return redirect('vault')

def pricing(request):        
    context = {'self_service_vaults':False, 'anonymous':True}
    if request.user.is_authenticated():
        context['anonymous'] = False
        if request.user.get_profile().has_feature('Self Service Vaults'):
            context['self_service_vaults'] = True
            context['current_plan'] = request.user.get_profile().plan
    return render_to_response('frontend/pricing.html', context,
      context_instance=RequestContext(request))
      
def corporate(request):
    context = {}
    if settings.DEBUG:
        return render_to_response('frontend/corporate/index.html', context, context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('frontpage'))
    
def test_error(request):
    raise Exception('failed in test_error')



###############################################################################
# Vault specific views
###############################################################################

maximum_vaults = {'free': 0, 'individual': 1, 'business': 5, 'corporate': 9999}

@login_required
def new_vault(request):
    profile = request.user.get_profile()
    plan = request.user.get_profile().plan
    vaults = Vault.objects.filter(user=profile.user)
    maximum = maximum_vaults[plan]
    if len(vaults) < maximum: 
        profile.create_vault('My New Vault')        
        return redirect('vault')
    else:
        return HttpResponseForbidden("You can't create a new vault. Please upgrade your ScraperWiki account.")

@login_required
def transfer_vault(request, vaultid, username):
    """
    When called by the owner of a vault, the ownership of the vault
    can be transfered to another account (whether they are currently a member or not).
    
    Once complete the access rights on all of the scrapers should also be 
    """
    mime = 'application/json'
            
    try:
        vault = Vault.objects.get(pk=vaultid)
    except:
        return HttpResponse('{"status": "fail", "error":"Could not find the requested vault"}', mimetype=mime)                    
        
    try:
        new_owner = User.objects.get(username=username )
    except:
        return HttpResponse('{"status": "fail", "error":"Cannot find that user"}', mimetype=mime)                    
    
    if not vault.user == request.user:
        return HttpResponse('{"status": "fail", "error":"You cannot transfer ownership of this vault"}', mimetype=mime)                    
        
    # Add the new owner as owner and as a member, the old owner will now just become 
    # a member instead
    vault.members.add(new_owner) 
    vault.user = new_owner
    vault.save()
    
    # Does not require the vault to be saved again
    vault.update_access_rights()
    return HttpResponse('{"status": "ok"}', mimetype=mime)       
    


@login_required
def view_vault(request, username=None):
    """
    View the details of the vault for the specific user.
    If they have no vault then nothing special happens.
    If they have just upgraded (check with a session variable), then
    they are thanked.
    """

    context = {}
    
    context['vaults'] = request.user.vaults
    context['vault_membership_count'] = request.user.vault_membership.exclude(user__id=request.user.id).count()
    context['vault_membership']  = request.user.vault_membership.all().exclude(user__id=request.user.id)
    context["api_base"] = "%s/api/1.0/" % settings.API_URL
    
    context['self_service_vaults'] = False
    if request.user.get_profile().has_feature('Self Service Vaults'):
        context['self_service_vaults'] = True
        context['current_plan'] = request.user.get_profile().plan
        context['vaults_remaining_in_plan'] = max(0, maximum_vaults[context['current_plan']] - context['vaults'].count())
        context['can_add_vault_members'] = ( context['current_plan'] in ('business','corporate',) )
    
    context['has_upgraded'] = False
    if request.session.get('recently_upgraded'):
        context['has_upgraded'] = True
        del request.session['recently_upgraded']
        
    return render_to_response('frontend/vault/view.html', context, 
                               context_instance=RequestContext(request))


@login_required
def vault_scrapers_remove(request, vaultid, shortname, newstatus):
    """
    Removes the scraper identified by shortname from the vault 
    identified by vaultid.  This can currently only be done by
    the vault owner, and only if the scraper is actually in the 
    vault.
    
    Will set the vault property of the scraper to None but does
    not touch the editorship/ownership which must be done elsewhere.
    """
#    if not request.is_ajax():
#        return HttpResponseForbidden('This page cannot be called directly')
    
    code = get_object_or_404( Code, short_name=shortname )
    vault   = get_object_or_404( Vault, pk=vaultid )
    mime = 'application/json'
    
    # Must own the vault
    if vault.user != request.user:
        return HttpResponse('{"status": "fail", "error":"You do not own this vault"}', mimetype=mime)            
    
    if code.vault != vault:
        return HttpResponse('{"status": "fail", "error":"This item is not in this vault"}', mimetype=mime)            

    
    code.privacy_status = newstatus
    code.vault = None
    code.save()

    return HttpResponse('{"status": "ok"}', mimetype=mime)                    

    
    
@login_required
def vault_scrapers_add(request, vaultid, shortname):
    """
    Adds a scraper identified by shortname to the vault (vaultid).

    The current user must be the current owner of the script and they
    must also be a member of the vault they are trying to add the 
    scraper to.
    
    During the transition, where the scraper's vault property is set
    the original owner is demoted to an editor, and the vault owner
    is set as owner (or promoted if they were an editor previously).
    """
#    if not request.is_ajax():
#        return HttpResponseForbidden('This page cannot be called directly')
    
    code = get_object_or_404( Code, short_name=shortname )
    vault   = get_object_or_404( Vault, pk=vaultid )
    mime = 'application/json'
    
    if not code.owner() == request.user:
        # Only the scraper owner can add it to a vault
        return HttpResponse('{"status": "fail", "error":"You cannot move this item to your own vault"}', mimetype=mime)            
            
    # Must be a member of the vault
    if not request.user in vault.members.all():
        return HttpResponse('{"status": "fail", "error":"You are not a member of this vault"}', mimetype=mime)            
            
    # Old owner is now editor and the new owner should be the vault owner.
    code.privacy_status = 'private'
    code.vault = vault
    code.generate_apikey()
    code.save()
    
    vault.update_access_rights()
                
    return HttpResponse('{"status": "ok" }', mimetype=mime)            
    
    
@login_required
def vault_users(request, vaultid, username, action):
    """
    View which allows a user to add/remove users from their vault. Will
    only work on the current user's vault so if they don't have one then
    it won't work.
    """
    if not request.is_ajax():
        return HttpResponseForbidden('This page cannot be called directly')
    
    from django.template.loader import render_to_string
    from codewiki.models import Vault
    mime = 'application/json'
     
    vault = get_object_or_404( Vault, id=vaultid)
    if vault.user.id != request.user.id:
        return HttpResponse('{"status": "fail", "error": "Not your vault"}', mimetype=mime)                    
        
    try:
        user = User.objects.get( username=username )    
    except User.DoesNotExist:
        return HttpResponse('{"status": "fail", "error":"Username not found"}', mimetype=mime)            

    result = {"status": "ok", "error":""}                    
    
    editor = request.user == vault.user
    
    if action =='adduser':
        if not user in vault.members.all():
            current_plan = request.user.get_profile().plan
            if current_plan not in ('business','corporate',):
                return HttpResponse('''{"status": "fail", "error":"You can't add users to this vault. Please upgrade your ScraperWiki account."}''', mimetype=mime)            
                
            result['fragment'] = render_to_string( 'frontend/includes/vault_member.html', { 'm' : user, 'vault': vault, 'editor' : editor })                 
            vault.members.add(user) 
            vault.add_user_rights(user)
        else:
            result['status'] = 'fail'
            result['error']  = 'User is already a member of this vault'
            
    if action =='removeuser':
        if user in vault.members.all():
            vault.members.remove(user)     
            vault.remove_user_rights(user)           
        else:
            result['status'] = 'fail'
            result['error']  = 'User not in this vault'
        
    vault.save()        
                
    
    return HttpResponse( json.dumps(result), mimetype=mime)





