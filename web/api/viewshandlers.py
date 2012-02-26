import urllib
import urllib2

from django.contrib.sites.models import Site

from django.conf import settings
from django.template import RequestContext, loader, Context
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from settings import MAX_API_ITEMS, API_URL
from django.views.decorators.http import condition
from tagging.models import Tag

from models import APIMetric
import csv
import datetime
import re
import PyRSS2Gen

from django.utils.encoding import smart_str
from django.core.serializers.json import DateTimeAwareJSONEncoder

from frontend.models import UserProfile

from codewiki.models import Scraper, Code, UserCodeRole, ScraperRunEvent, CodePermission, scraper_search_query, scraper_search_query_unordered, scrapers_overdue
from codewiki.managers.datastore import DataStore
import frontend
from cStringIO import StringIO

try:     import json
except:  import simplejson as json


def getscraperorresponse(short_name):
    try:
        scraper = Code.objects.get(short_name=short_name)
    except Code.DoesNotExist:
        return None, "Sorry, this scraper does not exist"
#    if not scraper.actionauthorized(user, "apidataread"):
#        return scraper.authorizationfailedmessage(user, "apidataread").get("body")
    return scraper, None
    

# see http://stackoverflow.com/questions/1189111/unicode-to-utf8-for-csv-files-python-via-xlrd
def stringnot(v):
    if v == None:
        return ""
    if type(v) in [unicode, str]:
        return v.encode("utf-8")
    return v


def stream_rows(dataproxy, format):
    n = 0
    while True:
        line = dataproxy.receiveonelinenj()
        try:
            ret = json.loads(line)
        except ValueError, e:
            yield str(e)
            break
        if "error" in ret:
            yield str(ret)
            break
        
        fout = StringIO()
        
            # csv and json numerical values are typed, but not htmltable numerics
        if format == "csv":
            writer = csv.writer(fout, dialect='excel')
            if n == 0:
                writer.writerow([ k.encode('utf-8') for k in ret["keys"] ])
            for row in ret["data"]:
                writer.writerow([ stringnot(v)  for v in row ])
        elif format == "htmltable":
            if n == 0:
                            # there seems to be an 8px margin imposed on the body tag when delivering a page that has no <body> tag
                fout.write('<table border="1" style="border-collapse:collapse; ">\n')
                fout.write("<tr> <th>%s</th> </tr>\n" % ("</th> <th>".join([ k.encode('utf-8') for k in ret["keys"] ])))
            for row in ret["data"]:
                fout.write("<tr> <td>%s</td> </tr>\n" % ("</td> <td>".join([ str(stringnot(v)).replace("<", "&lt;")  for v in row ])))
        else:
            assert False, "Bad format "+format
        
        yield fout.getvalue()
        n += 1
        if not ret.get("moredata"):
            if format == "htmltable":
                yield "</table>\n"
            break  
        




# formats that should be easy to stream because they are line based
# may also work for jsondict if we close the bracket ourselves
def out_csvhtml(dataproxy, short_name, format):
    strea = stream_rows(dataproxy, format)
    if format == "csv":
        mimetype = 'text/csv; charset=utf-8'
    else:
        mimetype = 'text/html; charset=utf-8'
        
    response = HttpResponse(mimetype=mimetype)  # used to take strea
    #response = HttpResponse(strea, mimetype='text/csv')  # when streamchunking was tried
    
    if format == "csv":
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % (short_name)
        
    for s in strea:
        response.write(s)

    dataproxy.close()
    
# unless you put in a content length, the middleware will measure the length of your data
# (unhelpfully consuming everything in your generator) before then returning a zero length result 
#response["Content-Length"] = 1000000000
    return response
    

# TODO: Fix this so that we can stream the results to either the browser
# or the download.  Currently this dies on large data ~38k rows (depending
# on query) with a timeout and so the user gets nothing, but maybe we should
# do iterating over the results as they come in and part-encoding the
# stream with each row?
def out_json(dataproxy, callback, short_name, format):
    # json is not chunked.  The output is of finite fixed bite sizes because
    # it is generally used by browsers which aren't going to survive a huge
    # download; however could chunk the jsondict type stream_wise as above
    # by manually creating the outer bracketing as with htmltable.

    result = dataproxy.receiveonelinenj()  # no streaming rows because streamchunking value was not set
    
    if not result:
        dataproxy.close()
        return HttpResponse("Error: Dataproxy responded with an invalid response")        

    if format == "jsondict":
        try:
            res = json.loads(result)

            while res.get('stillproducing') == 'yes':
                dresult = json.loads(dataproxy.receiveonelinenj())
                res['data'].extend(dresult['data'])
                res['stillproducing'] = dresult.get('stillproducing')

        except ValueError, e:
            dataproxy.close()            
            return HttpResponse("Error: %s" % (e.message,))
            
        if "error" not in res:
            dictlist = [ dict(zip(res["keys"], values))  for values in res["data"] ]
            result = json.dumps(dictlist, cls=DateTimeAwareJSONEncoder, indent=4)
    else:
        assert format == "jsonlist"
    if callback:
        result = "%s(%s)" % (callback, result)
    response = HttpResponse(result, mimetype='application/json; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=%s.json' % (short_name)
    
    dataproxy.close()
    return response

def out_rss2(dataproxy, scraper):
    result = dataproxy.receiveonelinenj()  # no streaming rows because streamchunking value was not set
    try:
        res = json.loads(result)
    except ValueError, e:
        return HttpResponse("Error:%s" % (e.message,))
    if "error" in res:
        return HttpResponse("Error2: %s" % res["error"])

    keymatches = { }
    if "guid" not in res["keys"] and "link" in res["keys"]:
        keymatches["guid"] = "link"
    if "pubDate" not in res["keys"] and "date" in res["keys"]:
        keymatches["pubDate"] = "date"
    rsskeys = ["title", "link", "description", "guid", "pubDate"]
    missingkeys = [ key  for key in rsskeys  if key not in res["keys"] and key not in keymatches ]
    if missingkeys:
        return HttpResponse("Error3: You are missing the following keys in the table: %s" % str(missingkeys))
        
    items = [ ]
    for value in res["data"]:
        ddata = dict(zip(res["keys"], value))
        
        # usual datetime conversion mess!
        spubDate = re.findall("\d+", ddata[keymatches.get("pubDate", "pubDate")])
        try:
            pubDate = datetime.datetime(*map(int, spubDate[:6]))
        except Exception, e:
            return HttpResponse("Date conversion error: %s\n%s" % (str(e), str(ddata)))
            
        guid = PyRSS2Gen.Guid(ddata[keymatches.get("guid", "guid")])
        rssitem = PyRSS2Gen.RSSItem(title=ddata["title"], link=ddata["link"], description=ddata["description"], guid=guid, pubDate=pubDate)
        items.append(rssitem)

    current_site = Site.objects.get_current()
    link = reverse('code_overview', args=[scraper.wiki_type, scraper.short_name])
    link = 'https://%s%s' % (current_site.domain,link,)

    rss = PyRSS2Gen.RSS2(title=scraper.title, link=link, description=scraper.description_safepart(), lastBuildDate=datetime.datetime.now(), items=items)

    fout = StringIO()
    rss.write_xml(fout)
    return HttpResponse(fout.getvalue(), mimetype='application/rss+xml; charset=utf-8')


# ***Streamchunking could all be working, but for not being able to set the Content-Length
# inexact values give errors in apache, so it would be handy if it could have a setting where 
# it organized some chunking instead

# see http://stackoverflow.com/questions/2922874/how-to-stream-an-httpresponse-with-django
# setting the Content-Length to -1 to prevent middleware from consuming the generator to measure it
# causes an error in the apache server.  same for a too long content length
# Should consider giving transfer-coding: chunked, 
# http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.6

# Streaming is only happening from the dataproxy into here.  Streaming
# from here out through django is  nearly impossible as we don't know
# the length of the output file if we incrementally build the csv output;
# the generator code has therefore been undone,
# all for want of setting response["Content-Length"] to the correct value.
@condition(etag_func=None)
def sqlite_handler(request):
    short_name = request.GET.get('name')
    apikey = request.GET.get('apikey', None)
    
    scraper,err = getscraperorresponse(short_name)
    if err:
        result = json.dumps({'error':err, "short_name":short_name})
        if request.GET.get("callback"):
            result = "%s(%s)" % (request.GET.get("callback"), result)
        return HttpResponse(result)
    
    u,s,kd = None, None, ""
    if request.user.is_authenticated():
        u = request.user
        
    if scraper.privacy_status != "private":
        s = scraper # XX why this only when not private? FAI
        kd = short_name
    else:
        # When private we MUST have an apikey and it should match
        if not scraper.api_actionauthorized(apikey):
            result = json.dumps({'error':"Invalid API Key", "short_name":short_name})
            if request.GET.get("callback"):
                result = "%s(%s)" % (request.GET.get("callback"), result)
            return HttpResponse(result)
            
    APIMetric.record( "sqlite", key_data=kd,  user=u, code_object=s )
    
    dataproxy = DataStore(request.GET.get('name'))
    lattachlist = request.GET.get('attach', '').split(";")
    attachlist = [ ]
    for aattach in lattachlist:
        if aattach:
            aa = aattach.split(",")
            attachi = {"name":aa[0], "asname":(len(aa) == 2 and aa[1] or None)}
            attachlist.append(attachi)
            dataproxy.request({"maincommand":"sqlitecommand", "command":"attach", "name":attachi["name"], "asname":attachi["asname"]})
    
    sqlquery = request.GET.get('query', "")
    format = request.GET.get("format", "json")
    if format == "json":
        format = "jsondict"
    
    req = {"maincommand":"sqliteexecute", "sqlquery":sqlquery, "data":None, "attachlist":attachlist}
    if format == "csv":
        req["streamchunking"] = 1000
    
    # This is inlined from the dataproxy.request() function to allow for
    # receiveoneline to perform multiple readlines in this case.
    # (this is the stream-chunking thing.  the right interface is not yet
    # apparent)
    
    dataproxy.m_socket.sendall(json.dumps(req) + '\n')
    
    if format not in ["jsondict", "jsonlist", "csv", "htmltable", "rss2"]:
        dataproxy.close()
        return HttpResponse("Error: the format '%s' is not supported" % format)


    if format in ["csv", 'htmltable']:   
        return out_csvhtml(dataproxy, scraper.short_name, format)
    if format == "rss2":
        return out_rss2(dataproxy, scraper)
        
    return  out_json(dataproxy, request.GET.get("callback"),
      scraper.short_name, format)
    

def scraper_search_handler(request):
    apikey = request.GET.get('apikey', None)
    
    query = request.GET.get('query') 
    if not query:
        query = request.GET.get('searchquery') 
    try:   
        maxrows = int(request.GET.get('maxrows', ""))
    except ValueError: 
        maxrows = 5
    result = [ ]  # list of dicts

    boverduescraperrequest = False
    if query == "*OVERDUE*":
        # We should check apikey against our shared secret. If it matches then it should
        # be allowed to continue.
        
        if request.META.get("HTTP_X_REAL_IP", "Not specified") in settings.INTERNAL_IPS:
            boverduescraperrequest = True
        if settings.INTERNAL_IPS == ["IGNORETHIS_IPS_CONSTRAINT"] or '127.0.0.1' in settings.INTERNAL_IPS:
            boverduescraperrequest = True
    else:
        u = None
        if request.user.is_authenticated():
            u = request.user
        APIMetric.record( "scrapersearch", key_data=query,  user=u, code_object=None )
        
    # TODO: If the user has specified an API key then we should pass them into
    # the search query and refine the resultset  to show only valid scrapers
    if boverduescraperrequest:
        scrapers_all = scrapers_overdue()  
    else:
        scrapers_all = scraper_search_query_unordered(user=None, query=query, apikey=apikey)


    # scrapers we don't want to be returned in the search
    nolist = request.GET.get("nolist", "").split()
    quietfields = request.GET.get('quietfields', "").split("|")
    #offset = request.GET.get('offset', 0)

    srequestinguser = request.GET.get("requestinguser", "")
    lrequestinguser = User.objects.filter(username=srequestinguser)
    if lrequestinguser:
        requestinguser = lrequestinguser[0]
    else:
        requestinguser = None

    # convert the query into an ordered list
    if boverduescraperrequest:
        scraperlist = scrapers_all
        
            # probably a way of sorting by some ranking on these ownership fields right in the database
    elif requestinguser:
        scraperlist = list(scrapers_all.distinct())
        for scraper in scraperlist:
            usercoderoles = UserCodeRole.objects.filter(code=scraper, user=requestinguser)
            if usercoderoles:
                if usercoderoles[0].role == "owner":
                    scraper.colleaguescore = (3, scraper.short_name)  # created_at
                elif usercoderoles[0].role == "editor":
                    scraper.colleaguescore = (2, scraper.short_name)  # created_at
                else:
                    scraper.colleaguescore = (1, scraper.short_name)  # created_at
            else:
                scraper.colleaguescore = (0, scraper.short_name)  # created_at
        scraperlist.sort(key=lambda user:user.colleaguescore, reverse=True)
    else:
        scrapers_all = scrapers_all.order_by('-created_at')
        scraperlist = scrapers_all.distinct()[:(maxrows+len(nolist))]

    for scraper in scraperlist:
        if scraper.short_name in nolist:
            continue
        res = {'short_name':scraper.short_name }
        res['title'] = scraper.title
        owners = scraper.userrolemap()["owner"]
        if owners:
            owner = owners[0]
            try:
                profile = owner.get_profile()
                ownername = profile.name
                if boverduescraperrequest:
                    res['beta_user'] = profile.beta_user   # to enable certain scrapers to go through the lxc process
            except frontend.models.UserProfile.DoesNotExist:
                ownername = owner.username
            if not ownername:
                ownername = owner.username
            if ownername:
                res['title'] = "%s / %s" % (ownername, scraper.title)
        if 'description' not in quietfields:
            res['description'] = scraper.description_safepart()
        res['created'] = scraper.created_at.isoformat()
        res['privacy_status'] = scraper.privacy_status
        res['language'] = scraper.language
        
        # extra data added to the overdue request kind so that twister has everything it needs to get on with it
        # and doesn't need to call back for further information
        if boverduescraperrequest:
            res['overdue_proportion'] = float(scraper.overdue_proportion)
            vcsstatus = scraper.get_vcs_status(-1)
            res['code'] = vcsstatus.get("code", "#Code not previously saved")
            res["rev"] = vcsstatus.get("prevcommit", {}).get("rev", -1)
            res['guid'] = scraper.guid
            res["attachables"] = [ ascraper.short_name  for ascraper in scraper.attachable_scraperdatabases() ]
            res["envvars"] = scraper.description_envvars()
            
        result.append(res)
        if len(result) > maxrows:
            break


    if request.GET.get("format") == "csv":
        fout = StringIO()
        writer = csv.writer(fout, dialect='excel')
        headers = [ 'short_name', 'title', 'description', 'created', 'privacy_status' ]
        writer.writerow(headers)
        for r in result:
            writer.writerow([r[header]  for header in headers])
        response = HttpResponse(fout.getvalue(), mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=search.csv'
        return response
    
    res = json.dumps(result, indent=4)
    callback = request.GET.get("callback")
    if callback:
        res = "%s(%s)" % (callback, res)
    response = HttpResponse(res, mimetype='application/json; charset=utf-8')
    #response['Content-Disposition'] = 'attachment; filename=search.json'
    return response



def usersearch_handler(request):
    query = request.GET.get('searchquery') 
    try:   
        maxrows = int(request.GET.get('maxrows', ""))
    except ValueError: 
        maxrows = 5
    
    u = None
    if request.user.is_authenticated():
        u = request.user
    APIMetric.record( "usersearch", key_data=query, user=u, code_object=None )
        
        # usernames we don't want to be returned in the search
    nolist = request.GET.get("nolist", "").split()
    
    srequestinguser = request.GET.get("requestinguser", "")
    lrequestinguser = User.objects.filter(username=srequestinguser)
    if lrequestinguser:
        requestinguser = lrequestinguser[0]
    else:
        requestinguser = None


    if query:
        users = User.objects.filter(username__icontains=query)
        userprofiles = User.objects.filter(userprofile__name__icontains=query)
        users_all = users | userprofiles
    else:
        users_all = User.objects.all()
    users_all = users_all.order_by('username')

        # if there is a requestinguser, then rank by overlaps and sort
        # (inefficient, but I got no other ideas right now)
        # (could be doing something with scraper.userrolemap())
    if requestinguser:
        requestuserscraperset = set([usercoderole.code.short_name  for usercoderole in requestinguser.usercoderole_set.all()])
        userlist = list(users_all)
        for user in userlist:
            user.colleaguescore = len(requestuserscraperset.intersection([usercoderole.code.short_name  for usercoderole in user.usercoderole_set.all()]))
        userlist.sort(key=lambda user:user.colleaguescore, reverse=True)
        #for user in userlist:
        #    print (user, user.colleaguescore)
    else:
        userlist = users_all[:(maxrows+len(nolist))]

    result = [ ]
    for user in userlist:
        if user.username not in nolist:
            res = {'username':user.username, "profilename":user.get_profile().name, "date_joined":user.date_joined.isoformat() }
            result.append(res)
        if len(result) > maxrows:
            break
    
    res = json.dumps(result, indent=4)
    callback = request.GET.get("callback")
    if callback:
        res = "%s(%s)" % (callback, res)
    
    response = HttpResponse(res, mimetype='application/json; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=search.json'
    return response


def userinfo_handler(request):
    username = request.GET.get('username', "")
    apikey = request.GET.get('apikey', "")
    users = User.objects.filter(username=username)
    result = [ ]
    for user in users:  # list of users is normally 1
        info = { "username":user.username, "profilename":user.get_profile().name }
        info["datejoined"] = user.date_joined.isoformat()
        info['coderoles'] = { }
        for ucrole in user.usercoderole_set.exclude(code__privacy_status="deleted"):
            if ucrole.code.privacy_status != "private":
                if ucrole.role not in info['coderoles']:
                    info['coderoles'][ucrole.role] = [ ]
                info['coderoles'][ucrole.role].append(ucrole.code.short_name)
            elif apikey:
                try:
                    api_user = UserProfile.objects.get(apikey=apikey).user
                    if api_user.usercoderole_set.filter(code__short_name=ucrole.code.short_name):
                        if ucrole.role not in info['coderoles']:
                            info['coderoles'][ucrole.role] = [ ]
                        info['coderoles'][ucrole.role].append(ucrole.code.short_name) 
                except UserProfile.DoesNotExist:
                    pass
                

        result.append(info)
    
    u = None
    if request.user.is_authenticated():
        u = request.user
    APIMetric.record( "getuserinfo", key_data=username,  user=u, code_object=None )

    res = json.dumps(result, indent=4)
    callback = request.GET.get("callback")
    if callback:
        res = "%s(%s)" % (callback, res)
    response = HttpResponse(res, mimetype='application/json; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=userinfo.json'
    return response


def runevent_handler(request):
    apikey = request.GET.get('apikey', None)
    
    short_name = request.GET.get('name')
    scraper,err = getscraperorresponse(short_name)
    if err:
        result = json.dumps({'error':err, "short_name":short_name})
        if request.GET.get("callback"):
            result = "%s(%s)" % (request.GET.get("callback"), result)
        return HttpResponse(result)

    kd = scraper.short_name
    s = scraper
    
    # Check accessibility if this scraper is private using 
    # apikey
    if not scraper.api_actionauthorized(apikey):
        result = json.dumps({'error':"Invalid API Key", "short_name":short_name})
        if request.GET.get("callback"):
            result = "%s(%s)" % (request.GET.get("callback"), result)
        return HttpResponse(result)
    if scraper.privacy_status == 'private': # XXX not sure why we do this, do metrics not work with private? FAI
        kd,s = '', None

    u = None
    if request.user.is_authenticated():
        u = request.user
    APIMetric.record( "runeventinfo", key_data=kd,  user=u, code_object=s )

        
    runid = request.GET.get('runid', '-1')
    runevent = None
    if scraper.wiki_type != "view":
            # negative index counts back from the most recent run
        if runid[0] == '-':
            try:
                i = -int(runid) - 1
                runevents = scraper.scraper.scraperrunevent_set.all().order_by('-run_started')
                if i < len(runevents):
                    runevent = runevents[i]
            except ValueError:
                pass
        if not runevent:
            try:
                runevent = scraper.scraper.scraperrunevent_set.get(run_id=runid)
            except ScraperRunEvent.DoesNotExist:
                pass
        
    if not runevent:
        result = json.dumps({'error':"run_event not found", "short_name":short_name})
        if request.GET.get("callback"):
            result = "%s(%s)" % (request.GET.get("callback"), result)
        return HttpResponse(result)

    info = { "runid":runevent.run_id, "run_started":runevent.run_started.isoformat(), 
             "records_produced":runevent.records_produced, "pages_scraped":runevent.pages_scraped }
    if runevent.run_ended:
        info['run_ended'] = runevent.run_ended.isoformat()
    if runevent.exception_message:
        info['exception_message'] = runevent.exception_message
    
    info['output'] = runevent.output
    if runevent.first_url_scraped:
        info['first_url_scraped'] = runevent.first_url_scraped
    
    domainsscraped = [ ]
    for domainscrape in runevent.domainscrape_set.all():
        domainsscraped.append({'domain':domainscrape.domain, 'bytes':domainscrape.bytes_scraped, 'pages':domainscrape.pages_scraped})
    if domainsscraped:
        info['domainsscraped'] = domainsscraped
        
    result = [info]      # a list with one element
    res = json.dumps(result, indent=4)
    callback = request.GET.get("callback")
    if callback:
        res = "%s(%s)" % (callback, res)
    response = HttpResponse(res, mimetype='application/json; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=runevent.json'
    return response



def convert_history(commitentry):
    result = { 'version':commitentry['rev'], 'date':commitentry['date'].isoformat() }
    if 'user' in commitentry:
        result["user"] = commitentry['user'].username
    lsession = commitentry['description'].split('|||')
    if len(lsession) == 2:
        result['session'] = lsession[0]
    return result

def convert_run_event(runevent):
    result = { "runid":runevent.run_id, "run_started":runevent.run_started.isoformat(), 
                "records_produced":runevent.records_produced, "pages_scraped":runevent.pages_scraped, 
                "still_running":(runevent.pid != -1),
                }
    if runevent.run_ended:
        result['last_update'] = runevent.run_ended.isoformat()
    if runevent.exception_message:
        result['exception_message'] = runevent.exception_message
    return result

def convert_date(date_str):
    if not date_str:
        return None
    try:
        #return datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return datetime.datetime(*map(int, re.findall("\d+", date_str)))  # should handle 2011-01-05 21:30:37
    except ValueError:
        return None


def scraperinfo_handler(request):
    result = [ ]
    
    apikey =request.GET.get('apikey', None)
    
    quietfields = request.GET.get('quietfields', "").split("|")
    history_start_date = convert_date(request.GET.get('history_start_date', None))
    
    
    try: 
        rev = int(request.GET.get('version', ''))
    except ValueError: 
        rev = None

    for short_name in request.GET.get('name', "").split():
        scraper,err = getscraperorresponse(short_name)

        if err:
            result = json.dumps({'error':err, "short_name":short_name})
            if request.GET.get("callback"):
                result = "%s(%s)" % (request.GET.get("callback"), result)
            return HttpResponse(result)

        
        # Check accessibility if this scraper is private using 
        # apikey
        if hasattr(scraper, "privacy_status") and scraper.privacy_status == 'private':            
            if not scraper.api_actionauthorized(apikey):
                scraper = u'Invalid API Key'
            
        if type(scraper) in [str, unicode]:
            result.append({'error':scraper, "short_name":short_name})
        else:
            result.append(scraperinfo(scraper, history_start_date, quietfields, rev))

    u = None
    if request.user.is_authenticated():
        u = request.user
    APIMetric.record( "getinfo", key_data=request.GET.get('name', ""),  user=u, code_object=None )

    res = json.dumps(result, indent=4)
    callback = request.GET.get("callback")
    if callback:
        res = "%s(%s)" % (callback, res)
    response = HttpResponse(res, mimetype='application/json; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=scraperinfo.json'
    return response


def scraperinfo(scraper, history_start_date, quietfields, rev):
    info = { }
    info['short_name']  = scraper.short_name
    info['language']    = scraper.language
    info['created']     = scraper.created_at.isoformat()
    
    info['title']       = scraper.title
    info['description'] = scraper.description_safepart()
    info['tags']        = [tag.name for tag in Tag.objects.get_for_object(scraper)]
    info['wiki_type']   = scraper.wiki_type
    info['privacy_status'] = scraper.privacy_status

    if scraper.wiki_type == 'scraper':
        info['last_run'] = scraper.scraper.last_run and scraper.scraper.last_run.isoformat() or ''
        info['run_interval'] = scraper.scraper.run_interval

    attachables = [ ]
    for cp in CodePermission.objects.filter(code=scraper).all():
        if cp.permitted_object.privacy_status != "deleted":
            attachables.append(cp.permitted_object.short_name)
    info["attachables"] = attachables
            
    # these ones have to be filtering out the incoming private scraper names
    # (the outgoing attach to list doesn't because they're refered in the code as well)
    info["attachable_here"] = [ ]
    for cp in CodePermission.objects.filter(permitted_object=scraper).all():
        if cp.code.privacy_status not in ["deleted", "private"]:
            info["attachable_here"].append(cp.code.short_name)

    if scraper.wiki_type == 'scraper':
        info['records']     = scraper.scraper.record_count  # old style datastore
        
        if 'datasummary' not in quietfields:
            dataproxy = DataStore(scraper.short_name)
            sqlitedata = dataproxy.request({"maincommand":"sqlitecommand", "command":"datasummary", "val1":0, "val2":None})
            if sqlitedata and type(sqlitedata) not in [str, unicode]:
                info['datasummary'] = sqlitedata
    
    if 'userroles' not in quietfields:
        info['userroles'] = { }
        for ucrole in scraper.usercoderole_set.all():
            if ucrole.role not in info['userroles']:
                info['userroles'][ucrole.role] = [ ]
            info['userroles'][ucrole.role].append(ucrole.user.username)
        
    status = scraper.get_vcs_status(rev)
    if 'code' not in quietfields:
        info['code'] = status["code"]
    
    for committag in ["currcommit", "prevcommit", "nextcommit"]:
        if committag not in quietfields:
            if committag in status:
                info[committag] = convert_history(status[committag])
    
    if "currcommit" not in status and "prevcommit" in status and not status["ismodified"]:
        if 'filemodifieddate' in status:
            info["modifiedcommitdifference"] = str(status["filemodifieddate"] - status["prevcommit"]["date"])
            info['filemodifieddate'] = status['filemodifieddate'].isoformat()

    if 'history' not in quietfields:
        history = [ ]
        commitentries = scraper.get_commit_log("code")
        for commitentry in commitentries:
            if history_start_date and commitentry['date'] < history_start_date:
                continue
            history.append(convert_history(commitentry))
        history.reverse()
        info['history'] = history
    
    if scraper.wiki_type == 'scraper' and 'runevents' not in quietfields:
        if history_start_date:
            runevents = scraper.scraper.scraperrunevent_set.filter(run_ended__gte=history_start_date).order_by('-run_started')
        else:
            runevents = scraper.scraper.scraperrunevent_set.all().order_by('-run_started')[:2]
            
        info['runevents'] = [ ]
        for runevent in runevents:
            info['runevents'].append(convert_run_event(runevent))

    return info
        
