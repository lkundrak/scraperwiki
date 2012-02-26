from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.contrib.auth.models import User
from django.views.decorators.http import condition
from django.shortcuts import get_object_or_404
from django.contrib import messages

from django.conf import settings

from managers.datastore import DataStore
from codewiki import models
from codeparsers import MakeDescriptionFromCode
import frontend

import urllib
import re
import urllib2
import base64
import datetime
import socket
import urlparse
import sys
import logging

logger = logging.getLogger(__name__)

try:                import json
except ImportError: import simplejson as json

PRIVACY_STATUSES = [ 'public', 'visible', 'private', 'deleted']

PRIVACY_STATUSES_UI = [ ('public', 'can be edited by anyone who is logged on'),
                        ('visible', 'can only be edited by those listed as editors'), 
                        ('private', 'cannot be seen by anyone except for the designated editors'), 
                        ('deleted', 'is deleted') 
                      ]


def getscraperorresponse(request, wiki_type, short_name, rdirect, action):
    # Got fed up of this returning one thing and having to check the type. 
    if action in ["delete_scraper", "delete_data"]:
        if not (request.method == 'POST' and request.POST.get(action, None) == '1'):
            raise SuspiciousOperation # not the best description of error, but best available, see comment on getscraperor404 below
    
    try:
        scraper = models.Code.objects.get(short_name=short_name)
    except models.Code.DoesNotExist:
        message =  "Sorry, that %s doesn't seem to exist" % wiki_type
        heading = "404: File not found"
        return None, HttpResponseNotFound(render_to_string('404.html', {'heading':heading, 'body':message}, context_instance=RequestContext(request)))
            
    if rdirect and wiki_type != scraper.wiki_type:
        return None,HttpResponseRedirect(reverse(rdirect, args=[scraper.wiki_type, short_name]))

    # Only a valid user can undo, and delete the scraper + data ...    
    if not scraper.actionauthorized(request.user, action):
        return None,HttpResponseForbidden(render_to_string('404.html', scraper.authorizationfailedmessage(request.user, action), context_instance=RequestContext(request)))
        
    return scraper, None


# XXX This should not throw 404s for malformed request or lack of permissions, but 
# unfortunately Django has no such built in exceptions. Could hand roll our own like this:
#   http://theglenbot.com/creating-a-custom-http403-exception-in-django/
# Am using PermissionDenied and SuspiciousOperation as partial workaround meanwhile, see:
#   http://groups.google.com/group/django-users/browse_thread/thread/8d3dda89858ff2ee
def getscraperor404(request, short_name, action, do_check=True):
    try:
        scraper = models.Code.objects.get(short_name=short_name)
    except models.Code.DoesNotExist:
        raise Http404
    
    if not scraper.actionauthorized(request.user, action):
        raise PermissionDenied
        
    # extra post conditions to make spoofing these calls a bit of a hassle
    if do_check:
        if action in ["changeadmin", "settags", "set_privacy_status", "change_attachables"]:
            if not (request.method == 'POST' and request.is_ajax()):
                raise SuspiciousOperation
    
        if action in ["schedule_scraper", "run_scraper", ]:
            if request.POST.get(action, None) != '1':
                raise SuspiciousOperation
        
    return scraper


def comments(request, wiki_type, short_name):
    scraper,resp = getscraperorresponse(request, wiki_type, short_name, "scraper_comments", "comments")
    if resp: return resp
    return HttpResponseRedirect(reverse('code_overview', kwargs={'wiki_type':wiki_type,'short_name':short_name}) + '#chat') 


def populate_itemlog(scraper, run_count=-1):
    itemlog = [ ]
    if run_count != -1:
        log = scraper.get_commit_log("code")[:run_count]
    else:
        log = scraper.get_commit_log("code")
        
    for commitentry in log:
        item = { "type":"commit", "rev":commitentry['rev'], "datetime":commitentry["date"] }
        if "user" in commitentry:
            item["user"] = commitentry["user"]
        item['earliesteditor'] = commitentry['description'].split('|||')
        if itemlog:
            item["prevrev"] = itemlog[-1]["rev"]
        item["groupkey"] = "commit|||"+ str(item['earliesteditor'])
        itemlog.append(item) 
    itemlog.reverse()
    
    # now obtain the run-events and sort together
    if scraper.wiki_type == 'scraper':
        runevents = scraper.scraper.scraperrunevent_set.all().order_by('-run_started','pid')
        if run_count != -1:
            runevents = runevents[:run_count]
        seen = []
        events = []
        for r in runevents:
            if not r.run_id in seen:
                seen.append( r.run_id )
                events.append( r )
            
        for runevent in events:
            item = { "type":"runevent", "runevent":runevent, "datetime":runevent.run_started }
            if runevent.run_ended:
                item["runduration"] = runevent.getduration()
                item["durationseconds"] = runevent.getdurationseconds()
            item["groupkey"] = "runevent"
            if runevent.exception_message:
                item["groupkey"] += "|||" + str(runevent.exception_message.encode('utf-8'))
            if runevent.pid != -1:
                item["groupkey"] += "|||" + str(runevent.pid)
            itemlog.append(item)
        
        itemlog.sort(key=lambda x: x["datetime"], reverse=True)
        return itemlog
        
def scraper_history(request, wiki_type, short_name):
    scraper,resp = getscraperorresponse(request, wiki_type, short_name, "scraper_history", "history")
    if resp: return resp
    
    context = { 'selected_tab': 'history', 'scraper': scraper, "user":request.user }

    context["itemlog"] = populate_itemlog(scraper)
    context["filestatus"] = scraper.get_file_status()
    
    return render_to_response('codewiki/history.html', context, context_instance=RequestContext(request))

###############################################################################
# Called as a result of a GIT PUSH when the callback is pointed at a specific 
# scraper, we will handle the incoming request only if the fields match what
# the owner told us about the scraper/git connection.
###############################################################################
def gitpush(request, wiki_type, short_name):
    if not request.method == 'POST':
        return HttpResponse("Error - not a post request")                    
        
    try:
        data = json.loads( request.raw_post_data )
    except:
        # We need to notify the user that the push request was not handled
        return HttpResponse("Error - no JSON found")            

    # TODO: Check the username,repo and filename in the scraper properties 
    # against the properties set in the scraper. If they match then go 
    # fetch the updated file and use it.
    
    scraper = get_object_or_404( Scraper, short_name=short_name)
    if scraper.privacy_status == 'deleted':
        raise Http404
    
    # Check the scraper properties.
        
    return HttpResponse("OK")




# Rewrite of the overview page by Zarino
def full_history(request, wiki_type, short_name):
    scraper,resp = getscraperorresponse(request, wiki_type, short_name, "code_overview", "overview")
    if resp: return resp
    
    ctx = { "scraper": scraper }
    return render_to_response('codewiki/full_history.html', ctx, context_instance=RequestContext(request))
    
    
def code_overview(request, wiki_type, short_name):
    from codewiki.models import ScraperRunEvent, DomainScrape
    
    scraper,resp = getscraperorresponse(request, wiki_type, short_name, "code_overview", "overview")
    if resp: return resp
    
    alert_test = request.GET.get('alert', '')
    if alert_test:
        from frontend.utilities.messages import send_message        
        if alert_test == '1':
            actions = [
                ("Secondary", reverse('code_overview', args=[wiki_type, short_name]), True,),
                ("Primary", reverse('code_overview', args=[wiki_type, short_name]), False,),            
            ]
            level = 'info'
        elif alert_test == '2':
            actions =  [ 
                ("Secondary", reverse('code_overview', args=[wiki_type, short_name]), True,),
                ("Primary", reverse('code_overview', args=[wiki_type, short_name]), False,),                
            ]
            level = 'warning'
        elif alert_test == '3':
            actions =  [ 
                ("Secondary", reverse('code_overview', args=[wiki_type, short_name]), True,),
                ("Primary", reverse('code_overview', args=[wiki_type, short_name]), False,),                
            ]
            level = 'error'
        else:
            actions = []
            
        send_message( request,{
            "message": "This is an example " + level + " alert",
            "level"  :  level,
            "actions":  actions,
        })        
    
    context = {'selected_tab':'overview', 'scraper':scraper }
    context["scraper_tags"] = scraper.gettags()
    context["userrolemap"] = scraper.userrolemap()

    context["schedule_options"] = list(models.SCHEDULE_OPTIONS)
    
    # if {% if a in b %} worked we wouldn't need these two
    context["user_owns_it"] = (request.user in context["userrolemap"]["owner"])
    if request.user.is_anonymous():
        context['user_edits_it'] = False
    elif scraper.privacy_status == 'public' and request.user.is_authenticated():
        context["user_edits_it"] = True;
    else:
        context["user_edits_it"] = (request.user in context["userrolemap"]["owner"]) or (request.user in context["userrolemap"]["editor"])


    context['user_can_set_hourly'] = False
    context['self_service_vaults'] = False
    if request.user.is_authenticated():
        context['user_plan'] = request.user.get_profile().plan
        if context['user_plan'] == 'business' or context['user_plan'] == 'corporate':
            context['user_can_set_hourly'] = True
        if request.user.get_profile().has_feature('Self Service Vaults'):
            context['self_service_vaults'] = True
        else:
            del(context["schedule_options"][4])
    else:
        context['user_plan'] = None
        del(context["schedule_options"][4])


    context["PRIVACY_STATUSES"] = PRIVACY_STATUSES_UI[0:2]  
    if request.user.is_staff:
        context["PRIVACY_STATUSES"] = PRIVACY_STATUSES_UI[0:3]  
    context["privacy_status_name"] = dict(PRIVACY_STATUSES_UI).get(scraper.privacy_status)

    context["api_base"] = "%s/api/1.0/" % settings.API_URL
            
    # view tpe
    if wiki_type == 'view':
        context["related_scrapers"] = scraper.relations.filter(wiki_type='scraper')
        if scraper.language == 'html':
            code = scraper.saved_code()
            if re.match('<div\s+class="inline">', code):
                context["htmlcode"] = code
        return render_to_response('codewiki/view_overview.html', context, context_instance=RequestContext(request))

    #
    # (else) scraper type section
    #
    assert wiki_type == 'scraper'

    context["related_views"] = models.View.objects.filter(relations=scraper).exclude(privacy_status="deleted")

    try:
        beta_user = request.user.get_profile().beta_user
    except frontend.models.UserProfile.DoesNotExist:
        beta_user = False
    except AttributeError:  # happens with AnonymousUser which has no get_profile function!
        beta_user = False

    context['forked_to'] = models.Scraper.objects.filter(forked_from=scraper).exclude(privacy_status='deleted').exclude(privacy_status='private').order_by('-created_at')[:5]
    context['forked_to_total'] = models.Scraper.objects.filter(forked_from=scraper).exclude(privacy_status='deleted').exclude(privacy_status='private').count()

    context['forked_to_remainder'] = int(models.Scraper.objects.filter(forked_from=scraper).exclude(privacy_status='deleted').exclude(privacy_status='private').count()) - 5;    

    #if dataproxy:
    #    dataproxy.close()

    try:
        event = ScraperRunEvent.objects.filter(scraper=scraper).order_by('-last_run')[0]
        context['domain_scrapes'] = DomainScrape.objects.filter(scraper_run_event=event).all()
    except:
        context['domain_scrapes'] = []

    context["itemlog"] = populate_itemlog(scraper, run_count=10)
            
    context['url_screenshot'] = None
    try:
        s = scraper.scraperrunevent_set.filter(first_url_scraped__isnull=False).order_by('run_started')[0]
        context['url_screenshot'] = s.first_url_scraped
    except:
        pass
            
    return render_to_response('codewiki/scraper_overview.html', context, context_instance=RequestContext(request))


# all remaining functions are ajax or temporary pages linked only 
# through the site, so throwing 404s is adequate

def scraper_admin_settags(request, short_name):
    scraper = getscraperor404(request, short_name, "settags")
    scraper.settags(request.POST.get('value', ''))  # splitting is in the library
    return HttpResponse("Successfully set new tags")

def scraper_admin_privacystatus(request, short_name):
    scraper = getscraperor404(request, short_name, "set_privacy_status")
    newvalue = request.POST.get('value', '')
    if newvalue and newvalue in PRIVACY_STATUSES:
        scraper.privacy_status = newvalue
        scraper.save()
    return HttpResponse(dict(PRIVACY_STATUSES_UI)[scraper.privacy_status])


def scraper_admin_controlattachables(request, short_name):
    scraper = getscraperor404(request, short_name, "change_attachables")

    attachablescraper_name = request.POST.get('attachable', '')
    if not attachablescraper_name:
        return HttpResponse("Failed: No attachable scraper included")
        
    try:
        attachablescraper = models.Code.objects.get(short_name=attachablescraper_name)
    except models.Code.DoesNotExist:
        return HttpResponse("Failed: attachable scraper does not exist")

    action = request.POST.get('action', '')
    if action == "remove":
            # have to allow this case in case there is an attachability to a scraper that has been deleted 
            # (scraper delete should make sure these are cleaned up; or better yet prevent deletion where there is a 
            # dependency, unless the deleted data gets forwarded to the successor scraper)
        #if attachablescraper.privacy_status == "deleted":
        #    return HttpResponse("Failed: attachable already deleted")
        if models.CodePermission.objects.filter(code=scraper, permitted_object=attachablescraper).count() == 0:
            return HttpResponse("Failed: scraper wasn't attachable anyway")
        models.CodePermission.objects.filter(code=scraper, permitted_object=attachablescraper).delete()
        return HttpResponse("Success: attachable scraper removed")

    if action != "add":
        return HttpResponse("Failed: action not recognized")

    if not attachablescraper.actionauthorized(request.user, "attachable_add"):
        return HttpResponse("Failed: only editors are allowed to add access to that scraper's datastore")
    
    if models.CodePermission.objects.filter(code=scraper, permitted_object=attachablescraper).count() != 0:
        return HttpResponse("Failed: attachable scraper already attached")

    models.CodePermission(code=scraper, permitted_object=attachablescraper).save()
    return HttpResponse("Success: attachable scraper added")
    

def scraper_admin_controleditors(request, short_name):
    username = request.GET.get('roleuser', '')
    newrole = request.GET.get('newrole', '')    
    processed = False

    if not username:
        return HttpResponse("Failed: username not provided")
        
    try:
        roleuser = User.objects.get(username=username)
    except User.DoesNotExist:
        return HttpResponse("Failed: username '%s' not found" % username)
    
    # We allow '' for removing a role
    if newrole not in ['editor', 'follow', '']:
        return HttpResponse("Failed: role '%s' unrecognized" % newrole)

    if newrole == '':
        # Make sure we are either removing the role from ourselves or have permission
        # to remove it from another user
        if request.user.id == roleuser.id:
            scraper = getscraperor404(request, short_name, "remove_self_editor")
        else:
            scraper = getscraperor404(request, short_name, "set_controleditors")
        
        # If the user is an owner and is trying to remove their own role then we 
        # should disregard this request as they cannot remove that role
        if models.UserCodeRole.objects.filter(code=scraper, user=roleuser, role='owner').count():
            return HttpResponse("Failed: You cannot remove yourself as owner" )                
        scraper.set_user_role(roleuser, 'editor', remove=True)
        context = { "role":'', "contributor":request.user }        
        processed = True        
    else:
        scraper = getscraperor404(request, short_name, "set_controleditors")

    if not processed:    
        if models.UserCodeRole.objects.filter(code=scraper, user=roleuser, role=newrole):
            return HttpResponse("Warning: user is already '%s'" % newrole)
    
        if models.UserCodeRole.objects.filter(code=scraper, user=roleuser, role='owner'):
            return HttpResponse("Failed: user is already owner")
        
        newuserrole = scraper.set_user_role(roleuser, newrole)
        context = { "role":newuserrole.role, "contributor":newuserrole.user }
        processed = True
        
    context["user_owns_it"] = (request.user in scraper.userrolemap()["owner"])
    if processed:
        return render_to_response('codewiki/includes/contributor.html', context, context_instance=RequestContext(request))
    return HttpResponse("Failed: unknown")



def view_admin(request, short_name):
    scraper = getscraperor404(request, short_name, "changeadmin")
    view = scraper.view

    response = HttpResponse()
    response_text = ''
    element_id = request.POST.get('id', None)
    if element_id == 'divAboutScraper':
        view.set_docs(request.POST.get('value', None), request.user)
        response_text = view.description_ashtml()

    if element_id == 'hCodeTitle':
        view.title = request.POST.get('value', None)
        response_text = view.title

    view.save()
    response.write(response_text)
    return response
    
    
def scraper_set_run_interval(request, short_name, value):
    try:
        scraper = getscraperor404(request, short_name, "changeadmin", do_check=False)
        scraper = scraper.scraper
        scraper.run_interval = int(value)
        scraper.save() # XXX need to save so template render gets new values, bad that it saves below also!
    except Exception, e:
        return HttpResponse('{"status":"error", "error":"Failed to update the schedule"}', mimetype='application/json')        
        
    return HttpResponse('{"status":"ok", "newvalue": "%s" }' % value, mimetype='application/json')

    
    
def scraper_admin(request, short_name):
    scraper = getscraperor404(request, short_name, "changeadmin")
    scraper = scraper.scraper
    
    response = HttpResponse()
    response_text = ''
    element_id = request.POST.get('id', None)
    if element_id == 'divAboutScraper':
        scraper.set_docs(request.POST.get('value', None), request.user)
        response_text = scraper.description_ashtml()
        
    if element_id == 'hCodeTitle':
        scraper.title = request.POST.get('value', None)
        response_text = scraper.title

    if element_id == 'spnRunInterval':
        scraper.run_interval = int(request.POST.get('value', None))
        scraper.save() # XXX need to save so template render gets new values, bad that it saves below also!
        context = {'scraper': scraper}
        context["user_owns_it"] = (request.user in scraper.userrolemap()["owner"])
        response_text = render_to_string('codewiki/includes/run_interval.html', context, context_instance=RequestContext(request))

    scraper.save()
    response.write(response_text)
    return response


def scraper_undo_delete_data(request, short_name):
    from frontend.utilities.messages import send_message
    
    scraper,resp = getscraperorresponse(request, "scraper", short_name, None, "undo_delete_data")
    if resp: return resp
    
    try:
        dataproxy = DataStore(scraper.short_name)
        dataproxy.request({"maincommand":"undelete_datastore"})
        scraper.scraper.update_meta()
        scraper.save()
        dataproxy.close()
    except:
        pass

    send_message( request,{
        "message": "Your data has been recovered",
        "level"  : "info",
        "actions":  [ ]
    })
        
    return HttpResponseRedirect(reverse('code_overview', args=[scraper.wiki_type, short_name]))


def scraper_delete_data(request, short_name):
    from frontend.utilities.messages import send_message
    
    scraper,resp = getscraperorresponse(request, "scraper", short_name, None, "delete_data")
    if resp: return resp
    
    try:
        dataproxy = DataStore(scraper.short_name)
        dataproxy.request({"maincommand":"clear_datastore"})
        scraper.scraper.update_meta()
        scraper.save()
        dataproxy.close()
    except:
        pass
        
    send_message( request, {
        "message": "Your data has been deleted",
        "level"  : "warning",
        "actions": 
            [ 
                ("Undo?", reverse('scraper_undo_delete_data', args=[short_name]), False,)
            ]
    } )
    
    return HttpResponseRedirect(reverse('code_overview', args=[scraper.wiki_type, short_name]))



def run_scraper(request, short_name):
    """
    Now setup to actually allow it to run even if it is not scheduled. We do this 
    by setting the run_interval to be about every 32 years, which should make twister
    panic and run it soon.  
    
    In future this needs moving to throwing a job onto a queue rather than depending on 
    twister
    """
    from codewiki.models import Scraper
    from codewiki.models.code import MAGIC_RUN_INTERVAL
    
    code = getscraperor404(request, short_name, "schedulescraper")
    if code.wiki_type == "scraper":
        # We can now conver the code object (sigh) into a scraper now that we know
        # we have permission to access it.
        scraper = Scraper.objects.get(short_name=short_name)
        
        if scraper.run_interval == -1:
            scraper.run_interval = MAGIC_RUN_INTERVAL
        scraper.last_run = None
        scraper.save()
        return HttpResponse('{"status":"ok"}', mimetype='application/json')
    
    return HttpResponse('{"status":"fail", "error": "Only scrapers can be scheduled to run"}',
                         mimetype='application/json')



def scraper_schedule_scraper(request, short_name):
    from codewiki.models.code import MAGIC_RUN_INTERVAL
    
    scraper = getscraperor404(request, short_name, "schedulescraper")
    if scraper.wiki_type == "scraper":
        scraper.last_run = None
        scraper.save()
    return HttpResponseRedirect(reverse('code_overview', args=[scraper.wiki_type, short_name]))



def scraper_delete_scraper(request, wiki_type, short_name):
    from frontend.utilities.messages import send_message            
    
    scraper,resp = getscraperorresponse(request, wiki_type, short_name, None, "delete_scraper")
    if resp: return resp
    
    scraper.previous_privacy = scraper.privacy_status
    scraper.privacy_status = "deleted"
    scraper.save()
    
    send_message( request, {
        "message": "Your %s has been deleted" % wiki_type,
        "level"  : "warning",
        "actions": 
            [ 
                ("Undo?", reverse('scraper_undelete_scraper', args=[wiki_type, short_name]), False,)
            ]
     } )

    return HttpResponseRedirect(reverse('dashboard'))


def scraper_undelete_scraper(request, wiki_type, short_name):
    from frontend.utilities.messages import send_message                
    from codewiki.models import Code
    
    scraper = get_object_or_404(Code, short_name=short_name)
    if scraper.privacy_status == "deleted" and scraper.owner() == request.user:
        scraper.privacy_status = scraper.vault and 'private' or scraper.previous_privacy
        scraper.save()
        
        send_message( request, {
            "message": "Your %s has been recovered" % wiki_type,
            "level"  : "info",
         } )
        
    return HttpResponseRedirect(reverse('code_overview', args=[wiki_type, short_name]))



    # this is for the purpose of editing the description, so must be controlled as it has secret password environment settings
def raw_about_markup(request, wiki_type, short_name):
    scraper,resp = getscraperorresponse(request, wiki_type, short_name, None, "getrawdescription")
    if resp:
        return HttpResponse("sorry, you do not have permission to edit the description of this scraper", mimetype='text/plain')

    return HttpResponse(scraper.description, mimetype='text/x-web-textile')


def choose_template(request, wiki_type):
    
    context = { "wiki_type":wiki_type }
    context["sourcescraper"] = request.GET.get('sourcescraper', '')
    
    vault = request.GET.get('vault', None)
    
    if request.user.is_authenticated():
        context['vault_membership_count'] = request.user.vault_membership.exclude(user__id=request.user.id).count()
        context['vault_membership']  = request.user.vault_membership.all().exclude(user__id=request.user.id)
    else:
        context['vault_membership_count'] = None
        context['vault_membership']  = None
        
    tpl = 'codewiki/includes/choose_template.html'
        
    vers =  models.code.SCRAPER_LANGUAGES_V        

    # Scraper or View?
    if wiki_type == "scraper":    
        src = models.code.SCRAPER_LANGUAGES
    else:
        src = models.code.VIEW_LANGUAGES            
            
    langs =  []
    for i,x in enumerate(src):
        langs.append( (x[0], x[1], vers[i]))      
          
    context["languages"] = langs
    context["vault_id"] = vault # May be none if it wasn't specified
    try:
        context['user_vaults'] = request.user.vaults
    except:
        context['user_vaults'] = None
            
    return render_to_response(tpl, context, context_instance=RequestContext(request))


def convtounicode(text):
    try:   return unicode(text)
    except UnicodeDecodeError:  pass
        
    try:   return unicode(text, encoding='utf8')
    except UnicodeDecodeError:  pass
    
    try:   return unicode(text, encoding='latin1')
    except UnicodeDecodeError:  pass
        
    return unicode(text, errors='replace')


def proxycached(request):
    from httplib import BadStatusLine
    from urlparse import urljoin
    
    cacheid = request.POST.get('cacheid', None)
    if not cacheid:   
        cacheid = request.GET.get('cacheid', None)
    
    if not cacheid:
        return HttpResponse(json.dumps({'type':'error', 'content':"No cacheid found"}), mimetype="application/json")
    
    proxyurl = urljoin(settings.HTTPPROXYURL , "/Page?" + cacheid )
    
    result = { 'proxyurl':proxyurl, 'cacheid':cacheid }
    
    try:
        fin = urllib2.urlopen(proxyurl)
        result["mimetype"] = fin.headers.type or "text/html"
        if fin.headers.maintype == 'text' or fin.headers.type == "application/json" or fin.headers.type[-4:] == "+xml":
            result['content'] = convtounicode(fin.read())
        else:
            result['content'] = base64.encodestring(fin.read())
            result['encoding'] = "base64"
    except urllib2.URLError, e: 
        result['type'] = 'exception'
        result['content'] = str(e)
        raise e
    except BadStatusLine, sl:
        result['type'] = 'exception'
        result['content'] = str(sl)
    except Exception, exc:
        result['type'] = 'exception'
        result['content'] = str(exc)
        raise exc
        
    return HttpResponse(json.dumps(result), mimetype="application/json")


# could be replaced with the dataproxy chunking technology now available in there,
# but as it's done, leave it here
def stream_sqlite(dataproxy, filesize, memblock):
    for offset in range(0, filesize, memblock):
        sqlitedata = dataproxy.request({"maincommand":"sqlitecommand", "command":"downloadsqlitefile", "seek":offset, "length":memblock})
        content = sqlitedata.get("content")
        if sqlitedata.get("encoding") == "base64":
            content = base64.decodestring(content)
        yield content
        assert len(content) == sqlitedata.get("length"), len(content)
        if sqlitedata.get("length") < memblock:
            break

# see http://stackoverflow.com/questions/2922874/how-to-stream-an-httpresponse-with-django
@condition(etag_func=None)
def export_sqlite(request, short_name):
    scraper = getscraperor404(request, short_name, "exportsqlite")
    memblock=100000
    
    dataproxy = DataStore(scraper.short_name)
    initsqlitedata = dataproxy.request({"maincommand":"sqlitecommand", "command":"downloadsqlitefile", "seek":0, "length":0})
    if "filesize" not in initsqlitedata:
        return HttpResponse(str(initsqlitedata), mimetype="text/plain")
    
    response = HttpResponse(stream_sqlite(dataproxy, initsqlitedata["filesize"], memblock), mimetype='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=%s.sqlite' % (short_name)
    response["Content-Length"] = initsqlitedata["filesize"]
    return response


# called back from the datastore for an scraper to ask whether it is allowed to attach to 
# the datastore for another scraper. 
# also automatically adds to the attachables list (encoded in CodePermission objects).
# this is close to how the user should experience it, but will need more security to 
# be assured that a user setting is there.  
# A user setting will only be there when it is running from the editor, in which case we will 
# grant access to scrapers which that user has access to, and send back a structured record 
# to the editor stating what has happened. 
# scheduled scrapers can't add new scrapers to this list, but will make a good enough error to explain it.
# the list of attachables should be passed through the controller when a scraper is run; 
# it will need including in the overdue scrapers list, as well as the stimulate_run record
def attachauth(request):
    scrapername = request.GET.get("scrapername")
    attachtoname = request.GET.get("attachtoname")

    fromscraper, toscraper = None, None
    if scrapername: 
        try:
            fromscraper = models.Code.objects.exclude(privacy_status="deleted").get(short_name=scrapername)
        except models.Code.DoesNotExist:
            return HttpResponse("Scraper does not exist: %s" % str([scrapername]))

    if attachtoname:
        try:
            toscraper = models.Code.objects.exclude(privacy_status="deleted").get(short_name=attachtoname)
        except models.Code.DoesNotExist:
            return HttpResponse("Scraper does not exist: %s" % str([scrapername]))

    if not toscraper:
        return HttpResponse("Need a 'to' scraper")
        
    if toscraper.privacy_status != 'private':
        # toscraper is public so anyone can read
        return HttpResponse("Yes")
    
    if not fromscraper:
        return HttpResponse("Need a 'from' scraper if not accessing public scraper")
    
    # If toscraper is private then it MUST be in a vault. 
    if fromscraper.privacy_status != 'private':
        return HttpResponse("Target scraper is private and source scraper is not in the vault")

    if not fromscraper.vault == toscraper.vault:
        return HttpResponse("Target scraper is not in the same vault as the source")        
        
    return HttpResponse("Yes")    
    
    
def webstore_attach_auth(request):
    mime = 'application/json'    
    scrapername = request.GET.get("scrapername")
    attachtoname = request.GET.get("attachtoname")

    fromscraper, toscraper = None, None
    if scrapername: 
        try:
            fromscraper = models.Code.objects.exclude(privacy_status="deleted").get(short_name=scrapername)
        except models.Code.DoesNotExist:
            return HttpResponse("{'attach':'Fail', 'error': 'Scraper does not exist: %s' % str([scrapername])}", mimetype=mime)

    if attachtoname:
        try:
            toscraper = models.Code.objects.exclude(privacy_status="deleted").get(short_name=attachtoname)
        except models.Code.DoesNotExist:
            return HttpResponse("{'attach':'Fail', 'error': 'Scraper does not exist: %s' % str([attachtoname])}", mimetype=mime)
        
    if not toscraper or not fromscraper:
        return HttpResponse("{'attach':'Fail', 'error': 'Need both a source and a target scraper'", mimetype=mime)

    if toscraper.privacy_status != 'private':
        # toscraper is public so anyone can read
            return HttpResponse("{'attach':'Ok'}", mimetype=mime)
    
    # If toscraper is private then it MUST be in a vault. 
    if fromscraper.privacy_status != 'private':
        return HttpResponse("{'attach':'Fail', 'error': 'Target scraper is private and source scraper is not in the vault'", mimetype=mime)        

    if not fromscraper.vault == toscraper.vault:
        return HttpResponse("{'attach':'Fail', 'error': 'Target scraper is not in the same vault as the source'", mimetype=mime)        
        
    return HttpResponse("{'attach':'Ok'}", mimetype=mime)
    

def scraper_data_view(request, wiki_type, short_name, table_name):
    """
    DataTable ( http://www.datatables.net/usage/server-side ) implementation for the new scraper page
    """
    from django.utils.html import escape
    mime = 'application/json'    
    
    def local_escape(s):
        if s is None:
            return ""
        return escape(s)
    
    if not wiki_type == 'scraper':
        # 415 - Unsupported Media Type
        # The entity of the request is in a format not supported by the requested resource
        return HttpResponse( status=415 )
    
    scraper,resp = getscraperorresponse( request, wiki_type, short_name, 
                                    "code_overview", "overview")    
    if resp: return resp
    
    # We have *mostly* validated the request now. So we need to load up the 
    # parameters we have been sent and the table_name we have been given and 
    # work out a query that satisfies it.  We also need to get the columns and 
    # put them in a list so that we can use them to sort on.
    offset      = int( request.REQUEST.get('iDisplayStart', '0')   )
    limit       = int( request.REQUEST.get('iDisplayLength', '10') )
    total_rows  = 0
    total_after_filter = 0
    sortbyidx = int( request.REQUEST.get('iSortCol_0','0') )
    sortdir = request.REQUEST.get('sSortDir_0', 'asc')

    columns = []
    data = []
    
    # Interact with the database
    dataproxy = None
    try:
        dataproxy = DataStore(scraper.short_name)
        
        # We will ask for a datasummary (pending new metadata call) 
        sqlite_data = dataproxy.request({"maincommand":"sqlitecommand", "command":"datasummary", "limit":1})
        if 'tables' in sqlite_data and table_name in sqlite_data['tables']:
            table = sqlite_data['tables'][table_name]
            total_rows = table['count']
            total_after_filter = total_rows
            sql = table['sql']
            columns = table['keys']
        else:
            raise Http404()
        
        sorting_columns = [ "`%s`" % c for c in columns]
        selecting_columns = [ "CASE WHEN length(`%s`)<1000 THEN `%s` ELSE substr(`%s`, 1, 1000)||'... {{MOAR||%s||'||rowid||'||NUFF}}' END AS `%s`" % (c,c,c,c,c) for c in columns]
        # jQuery can now use a regexp like...
        # {{MOAR\|\|([^\|]+)\|\|([^\|]+)\|\|NUFF}}$
        # ...to fish out the cell's column name and rowid
        # and show its full content if the user wants.
            
        # Build query and do the count for the same query
        sortby = "%s %s" % (sorting_columns[sortbyidx], sortdir,)
        query = 'select %s from `%s` order by %s limit %d offset %d' % (','.join(selecting_columns), table_name, sortby, limit, offset,)
        sqlite_data = dataproxy.request({"maincommand":"sqliteexecute", "sqlquery": query, "attachlist":"", "streamchunking": False, "data": ""})
        # We need to now convert this to the aaData list of lists
        if 'error' in sqlite_data:
            # Log the error
            data = [ ]
            logger.error("Error in scraper_data_view: " + str(sqlite_data))
        else:
            # For each row map each item in that row against escape
            data = map( lambda b: map(local_escape, b), sqlite_data['data'])
    except Exception, e:
        print e
    finally:
        if dataproxy:
            dataproxy.close()
    

    results = {
        'iTotalRecords'        : total_rows,
        'iTotalDisplayRecords' : total_after_filter,
        'sEcho'  : int( request.REQUEST.get('sEcho','0') ), # Cast at suggestion of docs
        'aaData' : data
    }
    return HttpResponse( json.dumps(results) , mimetype=mime)
    
