from django.template import RequestContext, TemplateDoesNotExist
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.views.decorators.cache import cache_page

from codewiki.models import Code, LANGUAGES_DICT

import os
import re
import codewiki
import settings
import urllib2
import urlparse
import cgi

def docmain(request, language=None, path=None):
    from titles import page_titles

    language_session = request.session.get('language', 'python')
    if not language and language_session:
        return HttpResponseRedirect(reverse('docsroot', kwargs={'language':language_session}) )
    language = language or language_session

    request.session['language'] = language
    context = {'language': language }
   
    # Which languages is this available for?
    context["lang_ruby"] = True
    context["lang_python"] = True
    context["lang_php"] = True
    # context["lang_javascript"] = True
    
    # not written by anyone yet
    if language == 'html':
        return HttpResponseRedirect(reverse('docsroot', kwargs={'language':'python'}) )
    if path in ['ruby_libraries', 'python_libraries', 'php_libraries', 'shared_libraries']:
        context["lang_shared"] = True
    
    if path in page_titles:
        title, para = page_titles[path]
        context["title"] = title
        context["para"] = para
        
        # Maybe we should be rendering a template from the file so that it isn't fixed 
        # as static html.
        context["docpage"] = 'documentation/includes/%s.html' % re.sub("\.\.", "", path)  # remove attempts to climb into another directory
        if not os.path.exists(os.path.join(settings.SCRAPERWIKI_DIR, "templates", context["docpage"])):
            raise Http404
    else:
        context["para"] = "Tutorials, references and guides for programmers coding on ScraperWiki"
        context["docindex"] = 1
            
    return render_to_response('documentation/docbase.html', context, context_instance=RequestContext(request))


def tutorials(request,language=None):
    from codewiki.models import Scraper, View

    if not language:
        return HttpResponseRedirect(reverse('tutorials',kwargs={'language': request.session.get('language', 'python')}) )

    tutorial_dict, viewtutorials = {}, {}
    tutorial_dict[language] = Scraper.objects.filter(privacy_status="public", istutorial=True, language=language).order_by('created_at')
        
    viewtutorials[language] = View.objects.filter(privacy_status="public", istutorial=True, language=language).order_by('created_at')

    context = {'language': language, 'tutorials': tutorial_dict, 'viewtutorials': viewtutorials}
    context['display_language'] = LANGUAGES_DICT[language]

    # Which languages is this available for?
    context["lang_ruby"] = True
    context["lang_python"] = True
    context["lang_php"] = True

    context["title"] = "Live tutorials"
    context["para"] = "Screen scraping tutorials entirely within a code editor in your browser"

    return render_to_response('documentation/tutorials.html', context, context_instance = RequestContext(request))


    # should also filter, say, on privacy_status=visible to limit what can be injected into here
def contrib(request, short_name):
    context = { }
    try:
        scraper = codewiki.models.Code.objects.filter().get(short_name=short_name) 
    except Code.DoesNotExist:
        raise Http404
    if not scraper.actionauthorized(request.user, "readcode"):
        raise PermissionDenied
    
    context["doccontents"] = scraper.get_vcs_status(-1)["code"]
    context["title"] = scraper.title

    context["scraper"] = scraper
    context["language"] = "python"
    return render_to_response('documentation/docbase.html', context, context_instance=RequestContext(request))


def docsexternal(request):
    language = request.session.get('language', 'python')
    api_base = "%s/api/1.0/" % settings.API_URL

    context = {'language':language, 'api_base':api_base }
    context["scrapername"] = request.GET.get("name", "")
    return render_to_response('documentation/apibase.html', context, context_instance=RequestContext(request))


def api_explorer(request):
    url = request.POST.get("apiurl")
    if not url:
        url = request.GET.get("apiurl")
    if not url:
        return HttpResponse('<pre style="color:#036;">%s</pre>' % "Select a function, add values above, \nthen click 'Run' to see live data")
    
    querystring = urlparse.urlparse(url)[4]
    params = dict(cgi.parse_qsl(querystring))
    format = params.get("format")
    
    api_base = "%s/api/1.0/" % settings.API_URL
    assert url[:len(api_base)] == api_base
    try:
        dresult = urllib2.urlopen(url).read()
    except urllib2.URLError:
        dresult = "Sorry, unable to open:\n%s\n\nThis error has been logged" % url
        #logger.log("api_explorer failed to load from %s" % url)
    
    if format == "htmltable":  # elements already escaped
        result = dresult
    else:
        result = '<pre style="color:#036;">%s</pre>' % re.sub("<", "&lt;", dresult)    # can't be done by formatting the iframe
    return HttpResponse(result)



