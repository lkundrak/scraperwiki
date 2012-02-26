import re
import sys
import unittest

from django.conf import settings
from django.http import HttpRequest
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.base import BaseHandler

from frontend.views import subscribe

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

def ensure_private_key_is_set():
    assert settings.RECURLY_PRIVATE_KEY != None

def rendered_subscribe_page():
    rf = RequestFactory()
    mock_request = rf.get('/subscribe/')
    response = subscribe(mock_request, 'individual')
    return response

def ensure_rendered_html_contains_signature():
    response = rendered_subscribe_page()
    assert 'signature' in response.content
    assert re.search(r"""signature: *['"][a-fA-F0-9-]+['"]""", response.content)

def ensure_rendered_html_contains_account_code():
    response = rendered_subscribe_page()
    assert re.search(r"""accountCode: *['"].+['"]""", response.content)
