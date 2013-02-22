#!/usr/bin/env python
# tests/testbase.py

"""unittest base class.  Intended to be subclassed by other
tests.

Assumes scriptmgr is already running."""

# http://docs.python.org/release/2.6.7/library/json.html
import json
# http://docs.python.org/release/2.6.7/library/unittest.html
import unittest
# http://docs.python.org/release/2.6.7/library/urllib.html
import urllib

class testBase(unittest.TestCase):
    """Does not contain any tests.  Subclass and add test*
    methods.
    """

    url = "http://127.0.0.1:9001/"

    def setUp(self):
        pass

    def Execute(self, code, language='python'):
        """Execute a script on the configured scriptmgr.
        """

        # http://docs.python.org/release/2.6.7/library/uuid.html
        import uuid

        # A random UUID.
        id = str(uuid.uuid4())

        d = {
            "runid" : id,
            "code": code,
            "scrapername": "test",
            "scraperid": id,
            "language": language
        }
        body = json.dumps(d)
        u = urllib.urlopen(self.URL("Execute"), data=body)
        return u.read()

    def URL(self, command):
        """Form a URL to access the scriptmgr by prefixing with
        the configured self.url.  *command* will typically be "Status"
        or "Execute" and so on (see scriptmgr.js for details).
        """
        return self.url + command

def console(response):
    """*response* is the entire response stream returned from
    scriptmgr.  Parse out the console messages from the JSON
    object sequence, and return all console output as a single
    string.
    """
    l = [ j for j in mjson(response) ]
    l = [ j['content'] for j in l
      if j['message_type'] == 'console' ]
    return ''.join(l)

def exceptions(response):
    """*response* is the entire response stream returned from
    scriptmgr (as for *console()*).  Parse out the exception
    messages, and return them all, converted using str,
    concatenated into a single string.
    """
    l = [ j for j in mjson(response) ]
    l = [ str(j) for j in l if j['message_type'] == 'exception' ]
    return ''.join(l)

def mjson(s):
    """*s* is a string holding one or more JSON objects that
    have been concatenated (multi-JSON); yield each JSON object
    in turn."""

    decode = json.JSONDecoder().raw_decode

    while True:
        o,i = decode(s)
        yield o
        s = s[i:].strip()
        if not s:
            break
