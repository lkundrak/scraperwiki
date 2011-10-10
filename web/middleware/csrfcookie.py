# Always set the CSRF cookie
# https://github.com/jorgebastida/django-dajaxice/issues/30
class CsrfAlwaysSetCookieMiddleware:
    def process_view(self, request, view_func, callback_args, callback_kwargs):
        request.META["CSRF_COOKIE_USED"] = True
        return None

