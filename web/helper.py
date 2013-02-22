import mock

from django.http import HttpRequest
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.base import BaseHandler
import django.core.mail

from frontend.views import subscribe

sent_mail_content = {}

def mock_sendmail(subject,message,from_email,recipient_list, **kwargs):
    global sent_mail_content
    sent_mail_content = dict(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list)

old_sendmail = django.core.mail.send_mail
django.core.mail.send_mail = mock_sendmail

##
## From http://djangosnippets.org/snippets/963/ and comments
class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.
    
    Usage:
    
    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})
    
    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client
    
    Once you have a request object you can pass it to any view function, 
    just as if that view had been hooked up using a URLconf.
    
    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        request = WSGIRequest(environ)
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request


