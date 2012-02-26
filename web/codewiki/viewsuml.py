from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from codewiki.models import Scraper, Code, ScraperRunEvent

import frontend

import re
import StringIO, csv, types
import datetime
import time
import os
import signal

from codewiki.util import kill_running_runid, get_overdue_scrapers

# Redirects to history page now, with # link to right place.
# NB: It only accepts the run_id hashes (NOT the Django id) so people can't
# run through every value and get the URL names of each scraper. It is
# for use in hyperlinks from the  status page where only the run id is known.
# Hyperlinks within scraper pages should use the Django id of the run and link
# to the # link in the history page.
def run_event(request, run_id):
    try:
        event = ScraperRunEvent.objects.get(run_id=run_id)
    except ScraperRunEvent.DoesNotExist:
        raise Http404
        
    scraper = event.scraper
    return HttpResponseRedirect(reverse('scraper_history', args=[scraper.wiki_type, scraper.short_name]) + "#run_" + str(event.id))


@login_required
def running_scrapers(request):
    if not request.user.is_staff:
        return HttpResponseRedirect( reverse('dashboard') )    
    recenteventsmax = 20
    recentevents = ScraperRunEvent.objects.all().order_by('-run_started')[:recenteventsmax]  
    context = { 'events':recentevents, 'eventsmax':recenteventsmax }
    context['overdue_count'] = get_overdue_scrapers().count()
    return render_to_response('codewiki/running_scrapers.html', context, context_instance=RequestContext(request))


@login_required
def status(request):
    if not request.user.is_staff:
        return HttpResponseRedirect( reverse('dashboard') )    
    recenteventsmax = 20
    recentevents = ScraperRunEvent.objects.all().order_by('-run_started')[:recenteventsmax]  
    context = { 'events':recentevents, 'eventsmax':recenteventsmax }
    context['overdue_count'] = get_overdue_scrapers().count()
    return render_to_response('codewiki/status.html', context, context_instance=RequestContext(request))


def scraper_killrunning(request, run_id, event_id):
    event = None
    if event_id or not request.user.is_staff:
        try:
            event = ScraperRunEvent.objects.get(id=event_id)
        except ScraperRunEvent.DoesNotExist:
            raise Http404
        if not event.scraper.actionauthorized(request.user, "killrunning"):
            raise PermissionDenied
        if request.POST.get('killrun', None) != '1':
            raise SuspiciousOperation

    killed = kill_running_runid(run_id)   # ought we be using the run event and seeing if we can kill it more smartly
    print "Kill function result on", killed
    time.sleep(1)
    if event:
        return HttpResponseRedirect(reverse('run_event', args=[event.run_id]))
    else:
        return HttpResponseRedirect(reverse('running_scrapers'))
        

