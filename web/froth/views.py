import json
from django.http import HttpResponse
from frontend.models import UserProfile


def check_key(request, apikey):
    p = UserProfile.objects.filter(apikey=apikey)
    print apikey, len(p)
    if len(p) == 0:
        status = 403 # Forbidden
        content = {'error':'Forbidden'}
    else:
        profile = p[0]
        content = {'org':profile.user.username}
        if profile.user.is_staff:
            status = 200 # Okay
        elif profile.plan == 'free':
            status = 402 # Pay
            content = {'error':'Pay'}
        else:
            status = 200 # Okay
    return HttpResponse(json.dumps(content), mimetype="text/plain", status=status)
