from django.conf import settings
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseServerError)
from django.views.decorators.csrf import csrf_exempt
from recuro import recurly_parser

@csrf_exempt
def notify(request, apikey):
    if apikey != settings.RECURLY_API_KEY:
        return HttpResponseForbidden()
    obj = recurly_parser.parse(request.raw_post_data)
    if obj == None:
        return HttpResponse("unsupported", mimetype="text/plain")

    resp, content = obj.save()

    if resp['status'] != '200':
        return HttpResponseServerError(content, mimetype="text/plain")

    return HttpResponse("ok", mimetype="text/plain")
