import base64
import hashlib
import urllib

from StringIO import StringIO
try:
    from M2Crypto import RSA
    from M2Crypto.BIO import MemoryBuffer
except:
    print "Could not import M2Crypto (in /web/recuro/xero.py)"
import oauth2
from django.conf import settings

class XeroPrivateClient(oauth2.Client):
    """
    Xero client for Private Application integration
    """
    def __init__(self, proxy_host=None, proxy_port=None):
        """Instantiate an authorised session to xero.
        """
        consumer_key = settings.XERO_CONSUMER_KEY
        consumer_secret = settings.XERO_CONSUMER_SECRET
        rsa_key = settings.XERO_RSA_KEY

        if proxy_host and proxy_port:
            proxy_info = httplib2.ProxyInfo(socks.PROXY_TYPE_HTTP, proxy_host,
                     proxy_port)
        else:
            proxy_info = None
        consumer = oauth2.Consumer(consumer_key, consumer_secret)
        # For private applications, the consumer key and secret are used as the
        # access token and access secret.
        token = oauth2.Token(consumer_key, consumer_secret)
        oauth2.Client.__init__(self, consumer, token, proxy_info=proxy_info)
        self.set_signature_method(SignatureMethod_RSA(rsa_key))

    def _xero_request(self, path, **k):
        sup = super(XeroPrivateClient, self)
        return sup.request("https://api.xero.com/api.xro/2.0%s" % path,
          **k)

    def save(self):
        """Add contact.  *xml* is a piece of XML in a string
        that specifies the Xero object to add.
        See http://blog.xero.com/developer/api/

        Return a (response, body) pair.  response['status']
        will give the HTTP status (as a string; '200' for okay).
        *body* is the body of the response.
        """

        body = urllib.urlencode(dict(xml=self.to_xml()))
        return self._xero_request("/%ss" % self.__class__.__name__
                                  , body=body, method="POST")

# Helpers

class SignatureMethod_RSA(oauth2.SignatureMethod):
    """ RSA signature not implemented by oauth2."""
    name = "RSA-SHA1"

    def __init__(self, key):
        super(oauth2.SignatureMethod, self).__init__()
        self.RSA = RSA.load_key_bio(MemoryBuffer(key))

    def signing_base(self, request):
        """Calculates the string that needs to be signed."""
        sig = (
            oauth2.escape(request.method),
            oauth2.escape(request.normalized_url),
            oauth2.escape(request.get_normalized_parameters()),
        )
        raw = '&'.join(sig)
        return raw

    def sign(self, request, consumer, token):
        """Returns the signature for the given request.
        Note: consumer and token are not used, but are there to fit in with
        call in oauth2 module.
        """
        raw = self.signing_base(request)
        digest = hashlib.sha1(raw).digest()
        signature = self.RSA.sign(digest, algo="sha1")
        encoded = base64.b64encode(signature)
        return encoded
