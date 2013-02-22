from django.contrib.auth.models import User

# See http://stackoverflow.com/questions/2242909/django-user-impersonation-by-admin
class ImpersonateMiddleware(object):
    def process_request(self, request):
        if request.user.is_superuser and "__impersonate" in request.GET:
            request.session['impersonate_username'] = str(request.GET["__impersonate"])
        elif "__unimpersonate" in request.GET:
            if 'impersonate_username' in request.session:
                del request.session['impersonate_username']
        if request.user.is_superuser and 'impersonate_username' in request.session:
            request.impersonated_by = request.user
            request.user = User.objects.get(username=request.session['impersonate_username'])

