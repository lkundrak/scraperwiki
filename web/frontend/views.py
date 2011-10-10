from django import forms
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.contrib import auth
from django.shortcuts import get_object_or_404
from django.conf import settings
from frontend.forms import SigninForm, UserProfileForm, SearchForm, ResendActivationEmailForm, DataEnquiryForm
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site

from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag, calculate_cloud, get_tag_list, LOGARITHMIC, get_queryset_and_model
from tagging.models import Tag, TaggedItem

from codewiki.models import UserUserRole, Code, UserCodeRole, Scraper,Vault, View, scraper_search_query, HELP_LANGUAGES, LANGUAGES_DICT
from django.db.models import Q
from frontend.forms import CreateAccountForm
from registration.backends import get_backend

# find this in lib/python/site-packages/profiles
from profiles import views as profile_views   

import django.contrib.auth.views
import os
import re
import datetime
import urllib
import itertools
import json

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
        tags.append(tag[0])
    
    data = {
			'featured_both': featured_both,
            'tags': tags, 
            'language': 'python'}
    return render_to_response('frontend/frontpage.html', data, context_instance=RequestContext(request))

@login_required
def dashboard(request, page_number=1):
    user = request.user
    owned_or_edited_code_objects = scraper_search_query(request.user, None).filter(usercoderole__user=user)
    #scrapers_all.filter((Q(usercoderole__user=user) & Q(usercoderole__role='owner')) | (Q(usercoderole__user=user) & Q(usercoderole__role='editor')))
    # v difficult to sort by owner and then editor status
        #owned_or_edited_code_objects = owned_or_edited_code_objects.order_by('usercoderole__role', '-created_at')
    
    paginator = Paginator(owned_or_edited_code_objects, settings.SCRAPERS_PER_PAGE)

    try:    page = int(page_number)
    except (ValueError, TypeError):   page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:     
        owned_or_edited_code_objects_pagenated = paginator.page(page)
    except (EmptyPage, InvalidPage):
        owned_or_edited_code_objects_pagenated = paginator.page(paginator.num_pages)
    
    context = {'owned_or_edited_code_objects_pagenated': owned_or_edited_code_objects_pagenated, 
               'language':'python' }
    return render_to_response('frontend/dashboard.html', context, context_instance = RequestContext(request))


# this goes through an unhelpfully located one-file app called 'profile' 
# located at scraperwiki/lib/python/site-packages/profiles   The templates are in web/templates/profiles
# It would help to copy the sourcecode into the main site to make it easier to find and maintain
def profile_detail(request, username):
    user = request.user
    profiled_user = get_object_or_404(User, username=username)
    
    # sorts against what the current user can see and what the identity of the profiled_user
    extra_context = { }
    owned_code_objects = scraper_search_query(request.user, None).filter(usercoderole__user=profiled_user)
    extra_context['owned_code_objects'] = owned_code_objects
    extra_context['emailer_code_objects'] = owned_code_objects.filter(Q(usercoderole__user__username=username) & Q(usercoderole__role='email'))
    extra_context['useruserrolemap'] = UserUserRole.useruserrolemap(profiled_user)
    return profile_views.profile_detail(request, username=username, extra_context=extra_context)


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
    return browse(request, page_number, wiki_type, special_filter)

def browse(request, page_number=1, wiki_type=None, special_filter=None):
    all_code_objects = scraper_search_query(request.user, None).select_related('owner','owner__userprofile_set')
    if wiki_type:
        all_code_objects = all_code_objects.filter(wiki_type=wiki_type) 

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


    # filter out scrapers that have no records
    if not special_filter:
        all_code_objects = all_code_objects.exclude(wiki_type='scraper', scraper__record_count=0)
    
    
    # Number of results to show from settings
    paginator = Paginator(all_code_objects, settings.SCRAPERS_PER_PAGE)

    try:
        page = int(page_number)
    except (ValueError, TypeError):
        page = 1

    if page == 1:
        featured_scrapers = Code.objects.filter(privacy_status="public", featured=True).order_by('-created_at')
    else:
        featured_scrapers = None

    # If page request (9999) is out of range, deliver last page of results.
    try:
        scrapers = paginator.page(page)
    except (EmptyPage, InvalidPage):
        scrapers = paginator.page(paginator.num_pages)

    form = SearchForm()

    dictionary = { "scrapers": scrapers, 'wiki_type':wiki_type, "form": form, "featured_scrapers":featured_scrapers, 'special_filter': special_filter, 'language': 'python'}
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

    url = urlparse(partial)
    dsqs = DomainScrape.objects.filter(scraper_run_event__scraper__privacy_status__in=['public','protected'],
                                       domain='%s://%s' % (url.scheme,url.netloc,) ).distinct('scraper_run_event__scraper')
    
    ctx = {
        'form'     : SearchForm(initial={'q': partial}),
        'scrapers_num_results'    : dsqs.count(),
        'scrapers' : [ d.scraper for d in dsqs.all().distinct() ],
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
        return render_to_response('frontend/search_results.html',
            {
                'scrapers': scrapers,
                'tags': tags,
                'scrapers_num_results': scrapers_num_results,
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


@login_required
def stats(request):
    return render_to_response('frontend/stats.html', {}, context_instance=RequestContext(request))
    

def tags(request):
    # would be good to limit this only to scrapers/views that this user has right to see (user_visible_code_objects; not the private ones), however 
    # the construction of the function tagging.models._get_usage() is a complex SQL query with group by 
    # that is not available in the django ORM.  
    all_tags = {}
    
    # trial code for filtering down by tags that you can't see
    if True:
        user_visible_code_objects = scraper_search_query(request.user, None)
        code_objects = user_visible_code_objects.extra(
            tables=['tagging_taggeditem', "tagging_tag"],
            where=['codewiki_code.id = tagging_taggeditem.object_id', 'tagging_taggeditem.tag_id = tagging_tag.id'], 
            select={"tag_name":"tagging_tag.name"})
        #print code_objects.query
        # This query needs to be annotated with a count(*) and a GROUP BY tagging_taggeditem.tag_id

        # sum through all the tags on all the objects
        lalltags = { }
        for x in code_objects:
            lalltags[x.tag_name] = lalltags.get(x.tag_name, 0)+1

        # convert above dict to format required by calculate_cloud
        # though you should be able to inline this function and change tags.html to avoid the need for <type Tag> objects
        for tag_name, count in lalltags.items():
            tag = Tag.objects.get(name=tag_name)
            tag.count = count
            all_tags[tag.name] = tag


    # old method that would show tags to scrapers that are private
    else:
        scraper_tags = Tag.objects.usage_for_model(Scraper, counts=True)
        view_tags = Tag.objects.usage_for_model(View, counts=True)
        for tag in itertools.chain(scraper_tags, view_tags):
            existing = all_tags.get(tag.name, None)
            if existing:
                existing.count += tag.count
            else:
                all_tags[tag.name] = tag

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
        return render_to_response('frontend/request_data_thanks.html', context_instance = RequestContext(request))
    return render_to_response('frontend/request_data.html', {'form': form}, context_instance = RequestContext(request))

def test_error(request):
    raise Exception('failed in test_error')



###############################################################################
# Vault specific views
###############################################################################

@login_required
def view_vault(request, username=None):
    """
    View the details of the vault for the specific user. If they have no vault
    then we will redirect to their dashboard as they shouldn't have been able
    to get here.
    """
    import logging
    from codewiki.models import Vault    
    context = {}
    
    if username is None:
        # Viewing vault for current user.
        vaults = request.user.vaults
        
    context['vaults'] = vaults
    context['vault_membership_count'] = request.user.vault_membership.exclude(user__id=request.user.id).count()
    context['vault_membership'] = request.user.vault_membership.all().exclude(user__id=request.user.id)
    context["api_base"] = "%s/api/1.0/" % settings.API_URL
        
    return render_to_response('frontend/vault/view.html', context, 
                               context_instance=RequestContext(request))


@login_required
def vault_scrapers_remove(request, vaultid, shortname):
    """
    Removes the scraper identified by shortname from the vault 
    identified by vaultid.  This can currently only be done by
    the vault owner, and only if the scraper is actually in the 
    vault.
    
    Will set the vault property of the scraper to None but does
    not touch the editorship/ownership which must be done elsewhere.
    """
    if not request.is_ajax():
        return HttpResponseForbidden('This page cannot be called directly')
    
    scraper = get_object_or_404( Scraper, short_name=shortname )
    vault   = get_object_or_404( Vault, pk=vaultid )
    mime = 'application/json'
    
    # Must own the vault
    if vault.user != request.user:
        return HttpResponse('{"status": "fail", "error":"You do not own this vault"}', mimetype=mime)            
    
    if scraper.vault != vault:
        return HttpResponse('{"status": "fail", "error":"The scraper is not in this vault"}', mimetype=mime)            
    
    # TODO: Decide how we remove the scraper from the vault other than just 
    # removing the vault propery
    
    scraper.vault = None
    scraper.save()

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
    if not request.is_ajax():
        return HttpResponseForbidden('This page cannot be called directly')
    
    scraper = get_object_or_404( Scraper, short_name=shortname )
    vault   = get_object_or_404( Vault, pk=vaultid )
    mime = 'application/json'
    
    if not scraper.owner() == request.user:
        # Only the scraper owner can add it to a vault
        return HttpResponse('{"status": "fail", "error":"You cannot move this scraper to your own vault"}', mimetype=mime)            
            
    # Must be a member of the vault
    if not request.user in vault.members.all():
        return HttpResponse('{"status": "fail", "error":"You are not a member of this vault"}', mimetype=mime)            
            
    # Old owner is now editor and the new owner should be the vault owner.
    scraper.privacy_status = 'private'
    scraper.vault = vault
    scraper.generate_apikey()
    scraper.save()
    
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





