from django.template import RequestContext
from django.template.loader import render_to_string
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotFound, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response,get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import mail_admins
from django.contrib.auth.decorators import login_required

from codewiki import models
import runsockettotwister
import frontend

import vc
import difflib
import re
import urllib
import os
import time

import uuid

try:                 import json
except ImportError:  import simplejson as json

# XXX not sure where this should go
def _datetime_to_epoch(dt):
    if dt:
        return time.mktime(dt.timetuple())
    return None


def getscraperor404(request, short_name, action):
    try:
        scraper = models.Code.objects.get(short_name=short_name)
    except models.Code.DoesNotExist:
        raise Http404
        
    if not scraper.actionauthorized(request.user, action):
        raise PermissionDenied

    return scraper

def raw(request, short_name):  
    """Raw code, as text/plain.  This is used by swimport, history diffs,
    "View Source", and probably others.
    """
    scraper = getscraperor404(request, short_name, "readcode")
    try:
        rev = int(request.GET.get('rev', '-1'))
    except ValueError:
        rev = -1

    # need to iterate back until we find the last change to the file
    while True:
        vcsstatus = scraper.get_vcs_status(rev)
        if "code" in vcsstatus:
            code = scraper.get_vcs_status(rev)["code"]
            break
        if "prevcommit" in vcsstatus:
            rev = vcsstatus["prevcommit"]["rev"]
        else:
            code = "*no code*"
            break
    return HttpResponse(code, mimetype="text/plain; charset=utf-8")


def diffseq(request, short_name):
    scraper = getscraperor404(request, short_name, "readcode")
    try: rev = int(request.GET.get('rev', '-1'))
    except ValueError: rev = -1
    try: otherrev = int(request.GET.get('otherrev', '-1'))
    except ValueError: otherrev = None

    code = scraper.get_vcs_status(rev)["code"]
    othercode = scraper.get_vcs_status(otherrev)["code"]

    sqm = difflib.SequenceMatcher(None, code.splitlines(), othercode.splitlines())
    result = sqm.get_opcodes()  # [ ("replace|delete|insert|equal", i1, i2, j1, j2) ]
    return HttpResponse(json.dumps(result))


# django-ids are used on history page.  runs from private scrapers give no information
def run_event_json(request, run_id):
    event = None
    try:
        event = models.ScraperRunEvent.objects.filter(run_id=run_id).order_by('pid')[0]
    except models.ScraperRunEvent.DoesNotExist:
        pass
    except models.ScraperRunEvent.MultipleObjectsReturned:
        pass
    except:
        pass

    if not event and re.match("\d+$", run_id):
        try:
            event = models.ScraperRunEvent.objects.filter(pk=run_id).order_by('pid')[0]
        except models.ScraperRunEvent.DoesNotExist:
            pass
        except:
            pass
            
    if not event:
        return HttpResponse(json.dumps({"error":"run event does not exist", "output":"ERROR: run event does not exist"}))
    
    if not event.scraper.actionauthorized(request.user, "readcode"):
        return HttpResponse(json.dumps({"error":"unauthorized", "output":"ERROR: unauthorized run event"}))
    
    result = { 'records_produced':event.records_produced, 'pages_scraped':event.pages_scraped, "output":event.output, 
               'first_url_scraped':event.first_url_scraped, 'exception_message':event.exception_message }
    if event.run_started:
        result['run_started'] = event.run_started.isoformat()
    if event.run_ended:
        result['run_ended'] = event.run_ended.isoformat()
        
    return HttpResponse(json.dumps(result))



def reload(request, short_name):
    scraper = getscraperor404(request, short_name, "readcode")
    oldcodeineditor = request.POST.get('oldcode')
    status = scraper.get_vcs_status(-1)
    result = { "code": status["code"], "rev":status.get('prevcommit',{}).get('rev', ''),
               "revdateepoch":_datetime_to_epoch(status.get('prevcommit',{}).get("date")) 
             }
    if oldcodeineditor:
        result["selrange"] = vc.DiffLineSequenceChanges(oldcodeineditor, status["code"])
    return HttpResponse(json.dumps(result))




blankstartupcode = { 'scraper' : { 'python': "import scraperwiki\n\n# Blank Python\n\n", 
                                    'php':   "<?php\n\n# Blank PHP\n\n?>\n", 
                                    'ruby':  "# Blank Ruby\n\n",
                                    'javascript': '// Blank Javascript scraper\n'
                                 }, 
                     'view'    : { 'python': "# Blank Python\nsourcescraper = ''\n", 
                                   'php':    "<?php\n# Blank PHP\n$sourcescraper = '';\n?>\n", 
                                   'ruby':   "# Blank Ruby\nsourcescraper = ''\n",
                                   'html':   "<p>Blank HTML page</p>\n",
                                   'javascript':"// Blank javascript\n",
                                  }
                   }

def newedit(request, short_name='__new__', wiki_type='scraper', language='python'):
    
    # quick and dirty corrections to incoming urls, which should really be filtered in the url.py settings
    language = language.lower()
    if language not in blankstartupcode[wiki_type]:
        language = 'python'
    
    context = {'selected_tab':'code'}
    
    if re.match('[\d\.\w]+$', request.GET.get('codemirrorversion', '')):
        context["codemirrorversion"] = request.GET.get('codemirrorversion')
    else:
        context["codemirrorversion"] = settings.CODEMIRROR_VERSION
        # should have really been tied in with codemirrorversion.  values can be plain,none or another editor when we have one
    context["texteditor"] = request.GET.get("texteditor", "codemirror")

    # if this is a matching draft scraper pull it in
    draftscraper = request.session.get('ScraperDraft')
    if draftscraper and draftscraper.get('scraper') and (short_name == "__new__" or draftscraper.get('scraper').short_name == short_name):
        scraper = draftscraper.get('scraper')
        
        context['code'] = draftscraper.get('code', ' missing')
        context['rev'] = 'draft'
        context['revdate'] = 'draft'
        context['revdateepoch'] = None

    # Load an existing scraper preference
    elif short_name != "__new__":
        try:
            scraper = models.Code.objects.get(short_name=short_name)
        except models.Code.DoesNotExist:
            message =  "Sorry, this %s does not exist" % wiki_type
            return HttpResponseNotFound(render_to_string('404.html', {'heading':'Not found', 'body':message}, context_instance=RequestContext(request)))
        if wiki_type != scraper.wiki_type:
            return HttpResponseRedirect(reverse("editor_edit", args=[scraper.wiki_type, short_name]))
        if not scraper.actionauthorized(request.user, "readcodeineditor"):
            return HttpResponseForbidden(render_to_string('404.html', scraper.authorizationfailedmessage(request.user, "readcodeineditor"), context_instance=RequestContext(request)))
       
        # link from history page can take us to "rollback" mode and see earlier revision
        rollback_rev = request.GET.get('rollback_rev', '')
        if rollback_rev != "":
            get_rev = int(rollback_rev)
            assert get_rev >= 0 # too confusing for now otherwise!
            context['rollback_rev'] = rollback_rev
            use_commit = 'currcommit'
        else:
            # default to getting most recent (from file should it have changed
            # but not been committed), hence the revision is always previous
            # commit
            get_rev = -1
            use_commit = 'prevcommit'

        status = scraper.get_vcs_status(get_rev)
        if rollback_rev == "":
            assert 'currcommit' not in status 

        # assert not status['ismodified']  # should hold, but disabling it for now
        if 'code' in status:
            context['code'] = status["code"]
        else:
            context['code'] = ''
        context['rev'] = status.get(use_commit,{}).get("rev", "0")
        context['revdate'] = status.get(use_commit,{}).get("date")
        context['revdateepoch'] = _datetime_to_epoch(context['revdate'])
        revuser = status.get(use_commit,{}).get("user")
        # If there is no user for the revision we should just use the scraper owner        
        if revuser is None:
            revuser = scraper.owner()
            
        context['revusername'] = revuser.username
        try:
            context['revuserrealname'] = revuser.get_profile().name
        except frontend.models.UserProfile.DoesNotExist:
            context['revuserrealname'] = revuser.username
        except AttributeError:  # happens with AnonymousUser which has no get_profile function!
            context['revuserrealname'] = revuser.username
                
    # create a temporary scraper object
    else:
        if wiki_type == 'view':
            scraper = models.View()
        else:
            scraper = models.Scraper()

        startupcode = blankstartupcode[wiki_type][language]
        
        startuptemplate = request.GET.get('template') or request.GET.get('fork')
        if startuptemplate:
            try:
                templatescraper = models.Code.objects.get(short_name=startuptemplate)
                if not templatescraper.actionauthorized(request.user, "readcode"):
                    startupcode = startupcode.replace("Blank", "Not authorized to read this code")
                else:
                    startupcode = templatescraper.saved_code()
                    if 'fork' in request.GET:
                        scraper.title = templatescraper.title
                        context['fork'] = request.GET.get('fork') # record as a fork
            except models.Code.DoesNotExist:
                startupcode = startupcode.replace("Blank", "Missing template for")

        context['rev'] = 'unsaved'
        context['revdate'] = 'unsaved'
        context['revdateepoch'] = None
            
        # replace the phrase: sourcescraper = 'working-example' with sourcescraper = 'replacement-name'
        inputscrapername = request.GET.get('sourcescraper', False)
        if inputscrapername:
            startupcode = re.sub('''(?<=sourcescraper = ["']).*?(?=["'])''', inputscrapername, startupcode)
        
        scraper.language = language
        context['code'] = startupcode


    #if a source scraper has been set, then pass it to the page
    if scraper.wiki_type == 'view' and request.GET.get('sourcescraper'):
        context['sourcescraper'] = request.GET.get('sourcescraper')

    context['scraper'] = scraper
    context['quick_help_template'] = 'codewiki/includes/%s_quick_help_%s.html' % (scraper.wiki_type, scraper.language.lower())

    if scraper.actionauthorized(request.user, "savecode") or context['rev'] in ('draft', 'unsaved'):
        context['savecode_authorized'] = "yes"
    
    return render_to_response('codewiki/neweditor.html', context, context_instance=RequestContext(request))


def edit(request, short_name='__new__', wiki_type='scraper', language='python'):
    
    # quick and dirty corrections to incoming urls, which should really be filtered in the url.py settings
    language = language.lower()
    if language not in blankstartupcode[wiki_type]:
        language = 'python'
    
    context = {'selected_tab':'code'}
    
    if re.match('[\d\.\w]+$', request.GET.get('codemirrorversion', '')):
        context["codemirrorversion"] = request.GET.get('codemirrorversion')
    else:
        context["codemirrorversion"] = settings.CODEMIRROR_VERSION
    context["codemirrorversion_main"] = context["codemirrorversion"][:1]   # 1 or 2

        # should have really been tied in with codemirrorversion.  values can be plain,none or another editor when we have one
    context["texteditor"] = request.GET.get("texteditor", "codemirror")

    # if this is a matching draft scraper pull it in
    draftscraper = request.session.get('ScraperDraft')
    if draftscraper and draftscraper.get('scraper') and (short_name == "__new__" or draftscraper.get('scraper').short_name == short_name):
        scraper = draftscraper.get('scraper')
        
        context['code'] = draftscraper.get('code', ' missing')
        context['rev'] = 'draft'
        context['revdate'] = 'draft'
        context['revdateepoch'] = None

    # Load an existing scraper preference
    elif short_name != "__new__":
        try:
            scraper = models.Code.objects.get(short_name=short_name)
        except models.Code.DoesNotExist:
            message =  "Sorry, this %s does not exist" % wiki_type
            return HttpResponseNotFound(render_to_string('404.html', {'heading':'Not found', 'body':message}, context_instance=RequestContext(request)))
        if wiki_type != scraper.wiki_type:
            return HttpResponseRedirect(reverse("editor_edit", args=[scraper.wiki_type, short_name]))
        if not scraper.actionauthorized(request.user, "readcodeineditor"):
            return HttpResponseForbidden(render_to_string('404.html', scraper.authorizationfailedmessage(request.user, "readcodeineditor"), context_instance=RequestContext(request)))
       
        # Link from history page can take us to "rollback" mode,
        # and see earlier revision.
        rollback_rev = request.GET.get('rollback_rev', '')
        try:
            get_rev = int(rollback_rev)
        except ValueError:
            rollback_rev = ''
        if rollback_rev:
            context['rollback_rev'] = rollback_rev
            use_commit = 'currcommit'
        else:
            # Default to getting most recent (from file should it have changed
            # but not been committed), hence the revision is always previous
            # commit.
            get_rev = -1
            use_commit = 'prevcommit'

        status = scraper.get_vcs_status(get_rev)
        if rollback_rev == "":
            assert 'currcommit' not in status 

        # assert not status['ismodified']  # should hold, but disabling it for now
        context['code'] = status["code"]
        context['rev'] = status.get(use_commit,{}).get("rev", "0")
        context['revdate'] = status.get(use_commit,{}).get("date")
        context['revdateepoch'] = _datetime_to_epoch(context['revdate'])
        revuser = status.get(use_commit,{}).get("user")
        # If there is no user for the revision we should just use the scraper owner        
        if revuser is None:
            revuser = scraper.owner()
            
        context['revusername'] = revuser and revuser.username or 'unknown'
        try:
            if revuser:
                context['revuserrealname'] = revuser.get_profile().name
            else:                            
                context['revuserrealname'] = 'Unknown'
        except frontend.models.UserProfile.DoesNotExist:
            context['revuserrealname'] = revuser.username
        except AttributeError:  # happens with AnonymousUser which has no get_profile function!
            context['revuserrealname'] = revuser.username
                
    # create a temporary scraper object
    else:
        if wiki_type == 'view':
            scraper = models.View()
        else:
            scraper = models.Scraper()

        startupcode = blankstartupcode[wiki_type][language]
        
        startuptemplate = request.GET.get('template') or request.GET.get('fork')
        if startuptemplate:
            try:
                templatescraper = models.Code.objects.get(short_name=startuptemplate)
                if not templatescraper.actionauthorized(request.user, "readcode"):
                    startupcode = startupcode.replace("Blank", "Not authorized to read this code")
                else:
                    startupcode = templatescraper.saved_code()
                    if 'fork' in request.GET:
                        scraper.title = templatescraper.title
                        context['fork'] = request.GET.get('fork') # record as a fork
            except models.Code.DoesNotExist:
                startupcode = startupcode.replace("Blank", "Missing template for")

        context['rev'] = 'unsaved'
        context['revdate'] = 'unsaved'
        context['revdateepoch'] = None
            
        # replace the phrase: sourcescraper = 'working-example' with sourcescraper = 'replacement-name'
        inputscrapername = request.GET.get('sourcescraper', False)
        if inputscrapername:
            startupcode = re.sub('''(?<=sourcescraper = ["']).*?(?=["'])''', inputscrapername, startupcode)
        
        scraper.language = language
        context['code'] = startupcode


    #if a source scraper has been set, then pass it to the page
    if scraper.wiki_type == 'view' and request.GET.get('sourcescraper'):
        context['sourcescraper'] = request.GET.get('sourcescraper')

    context['scraper'] = scraper
    context['quick_help_template'] = 'codewiki/includes/%s_quick_help_%s.html' % (scraper.wiki_type, scraper.language.lower())

    if scraper.actionauthorized(request.user, "savecode") or context['rev'] in ('draft', 'unsaved'):
        context['savecode_authorized'] = "yes"
    
    return render_to_response('codewiki/editor.html', context, context_instance=RequestContext(request))



# save a code object (source scraper is to make thin link from the view to the scraper
# this is called in two places, due to those draft scrapers saved in the session
# would be better if the saving was deferred and not done right following a sign in
def save_code(code_object, user, code_text, earliesteditor, commitmessage, sourcescraper=''):
    assert code_object.actionauthorized(user, "savecode")
    code_object.line_count = int(code_text.count("\n"))
    
    # work around the botched code/views/scraper inheretance.  
    # if publishing for the first time set the first published date
    
    code_object.save()  # save the object using the base class (otherwise causes a major failure if it doesn't exist)
    commit_message = earliesteditor and ("%s|||%s" % (earliesteditor, commitmessage)) or commitmessage
    rev = code_object.commit_code(code_text, commit_message, user)

    if code_object.wiki_type == "scraper":
        pass
    else: # XXX this should be only if "view" ?
        # make link to source scraper
        if sourcescraper:
            lsourcescraper = models.Code.objects.exclude(privacy_status="deleted").filter(short_name=sourcescraper)
            if lsourcescraper:
                code_object.relations.add(lsourcescraper[0])

    # Add user roles (including special case for first time
    if code_object.owner():
        if code_object.owner().pk != user.pk:
            code_object.add_user_role(user, 'editor')
    else:
        code_object.add_user_role(user, 'owner')

    # get the rev number even when no change
    status = code_object.get_vcs_status(-1)
    assert 'currcommit' not in status
    if rev != None:
        assert rev == status.get('prevcommit',{}).get("rev")
    else:  # case of no commit because files were the same
        rev = status.get('prevcommit',{}).get("rev")
    revdate = status.get('prevcommit',{}).get("date")
    
    return (rev, revdate) # None if no change


# called from the editor
def handle_editor_save(request):
    guid = request.POST.get('guid', '')
    title = request.POST.get('title', '')
    language = request.POST.get('language', '').lower()
    code = request.POST.get('code', "")
    stimulaterun = request.POST.get('stimulate_run', '')
    
    if not title or title.lower() == 'untitled':
        return HttpResponse(json.dumps({'status' : 'Failed', 'message':"title is blank or untitled"}))
    
    target_priv, fork = None, None    
    if guid:
        try:
            scraper = models.Code.objects.exclude(privacy_status="deleted").get(guid=guid)   # should this use short_name?
        except models.Code.DoesNotExist:
            return HttpResponse(json.dumps({'status' : 'Failed', 'message':"Name or guid invalid"}))
        
        assert scraper.language.lower() == language
        assert scraper.wiki_type == request.POST.get('wiki_type', '')
        scraper.title = title   # the save is done on save_code
        
        # over-write the "maintenance required" flag as soon as the user does anything with it
        # (there's been quite a mis-design here, but can live with it)
        if scraper.status == "sick":
            scraper.status = "ok"
        
    else:
        if request.POST.get('wiki_type') == 'view':
            scraper = models.View()
        else:
            scraper = models.Scraper()
        scraper.language = language
        scraper.title = title

        fork = request.POST.get("fork", None)
        if fork:
            try:
                scraper.forked_from = models.Code.objects.exclude(privacy_status="deleted").get(short_name=fork)
                if scraper.forked_from.vault:
                    target_priv = 'private'
                    scraper.set_invault = scraper.forked_from.vault
                else:
                    target_priv = scraper.forked_from.privacy_status
                    
            except models.Code.DoesNotExist:
                pass

    earliesteditor = request.POST.get('earliesteditor', "")
    sourcescraper = request.POST.get('sourcescraper', "")
    commitmessage = request.POST.get('commit_message', "")

    # quick sneak in and advance save to get rev number
    if request.user.is_authenticated() and scraper.actionauthorized(request.user, "savecode"):
        advancesave = save_code(scraper, request.user, code, earliesteditor, commitmessage, sourcescraper)  
    else:
        advancesave = None
    
    if stimulaterun in ["editorstimulaterun", "editorstimulaterun_nosave"]:
        clientnumber = int(request.POST.get('clientnumber', '-1'))
        urlquery = request.POST.get('urlquery', '')
        if request.user.is_authenticated() and scraper.actionauthorized(request.user, "stimulate_run"):
            runnerstream = runsockettotwister.RunnerSocket()
            rev = (advancesave and advancesave[0])
            stimulaterunmessage = runnerstream.stimulate_run_from_editor(scraper, request.user, clientnumber, language, code, rev, urlquery)
        else:
            stimulaterunmessage = {"message":"not authorised to run"}

    if stimulaterun == "editorstimulaterun_nosave":
        stimulaterunmessage['status'] = 'notsaved'
        return HttpResponse(json.dumps(stimulaterunmessage))
    
    # User is signed in, we can save the scraper 
    # (some of the operation was moved to advancesave so we have the 
    # rev number to pass to the runner in advance.  All this needs refactoring)
    if request.user.is_authenticated():
        if not scraper.actionauthorized(request.user, "savecode") and not request.user == scraper.owner():
            return HttpResponse(json.dumps({'status':'Failed', 'message':"Not allowed to save this scraper"}))
        
        if not advancesave:
            (rev, revdate) = save_code(scraper, request.user, code, earliesteditor, commitmessage, sourcescraper)  
        else:
            (rev, revdate) = advancesave
            
        if target_priv:
            scraper.privacy_status = target_priv
            scraper.save()
                                
        if hasattr(scraper, 'set_invault') and scraper.set_invault:
            scraper.vault = scraper.set_invault
            scraper.save()
            scraper.vault.update_access_rights()
            
        if fork:
            # Copy across the screenshot from the original            
            import logging
            if scraper.forked_from and scraper.forked_from.has_screenshot():
                import shutil
                try:
                    src = scraper.forked_from.get_screenshot_filepath()
                    rt, ext = os.path.splitext(src)
                    dst = os.path.join( os.path.dirname(src), scraper.short_name ) + ext
                    shutil.copyfile(src, dst)
                    scraper.has_screen_shot = True
                    scraper.save()
                except Exception, e:
                    logging.error( str(e) )
        

        response_url = reverse('editor_edit', kwargs={'wiki_type': scraper.wiki_type, 'short_name': scraper.short_name})
        return HttpResponse(json.dumps({'redirect':'true', 'url':response_url, 'rev':rev, 'revdateepoch':_datetime_to_epoch(revdate) }))

    # User is not logged in, save the scraper to the session
    else:
        draft_session_scraper = { 'scraper':scraper, 'code':code, 'sourcescraper': sourcescraper }
        request.session['ScraperDraft'] = draft_session_scraper

        # Set a message with django_notify telling the user their scraper is safe
        response_url = reverse('editor', kwargs={'wiki_type': scraper.wiki_type, 'language': scraper.language.lower()})
        return HttpResponse(json.dumps({'status':'OK', 'draft':'True', 'url':response_url}))


# retrieves draft scraper, saves and goes to the editor page
def handle_session_draft(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('login') + "?next=%s" % reverse('handle_session_draft'))

    session_scraper_draft = request.session.pop('ScraperDraft', None)
    if not session_scraper_draft:  # shouldn't be here
        return HttpResponseRedirect(reverse('frontpage'))

    draft_scraper = session_scraper_draft.get('scraper', None)
    draft_scraper.save()
    draft_code = session_scraper_draft.get('code')
    sourcescraper = session_scraper_draft.get('sourcescraper')
    commitmessage = session_scraper_draft.get('commit_message', "") # needed?
    earliesteditor = session_scraper_draft.get('earliesteditor', "") #needed?
        
        # we reload into editor but only save for an authorized user
    if draft_scraper.actionauthorized(request.user, "savecode"):
        save_code(draft_scraper, request.user, draft_code, earliesteditor, commitmessage, sourcescraper)
        if 'ScraperDraft' in request.session:
            del request.session['ScraperDraft']        

    response_url = reverse('editor_edit', kwargs={'wiki_type': draft_scraper.wiki_type, 'short_name' : draft_scraper.short_name})
    return HttpResponseRedirect(response_url)


def delete_draft(request):
    if request.session.get('ScraperDraft', False):
        del request.session['ScraperDraft']
    request.notifications.used = True   # Remove any pending notifications, i.e. the "don't worry, your scraper is safe" one
    return HttpResponseRedirect(reverse('frontpage'))
def quickhelp(request):
    query = dict([(k, request.GET.get(k, "").encode('utf-8'))  for k in ["language", "short_name", "username", "wiki_type", "line", "character", "word"]])
    if re.match("http://", query["word"]):
        query["escapedurl"] = urllib.quote(query["word"])
    
    context = query.copy()
    context['quick_help_template'] = 'documentation/%s_quick_help_%s.html' % (query["wiki_type"], query["language"])
    context['query_string'] = urllib.urlencode(query)
    return render_to_response('documentation/quick_help.html', context, context_instance=RequestContext(request))


@login_required
def add_to_vault(request, wiki_type, language, id):
    """
    Create a new scraper with the specific type and language, put it in the vault (if
    the current user is allowed and then we're done)
    """
    from codewiki.models import Vault, Scraper, View, UserCodeRole
    
    name = request.GET.get('name', None)
    
    if not name:
        return HttpResponseForbidden("A name is required")        
    
    vault = get_object_or_404(Vault, pk=id)
    if not request.user in vault.members.all():
        return HttpResponseForbidden("You cannot access this vault")             

    if wiki_type == 'scraper':
        scraper = Scraper()
    else:
        scraper = View()
    scraper.title = name
    scraper.language = language
    scraper.privacy_status = 'private'
    scraper.vault = vault
    scraper.generate_apikey()
    scraper.save()
    
    # Make sure we update the access rights
    vault.update_access_rights()
    scraper.commit_code(blankstartupcode[wiki_type][language], "Created", request.user)
    
    response_url = reverse('editor_edit', kwargs={'wiki_type': wiki_type, 'short_name' : scraper.short_name})
    return HttpResponseRedirect(response_url)
