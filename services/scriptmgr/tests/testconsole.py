#!/usr/bin/env python
# tests/testconsole.py

"""Tests the console I/O functionality of scriptmgr.

Assumes scriptmgr is already running."""

# http://docs.python.org/release/2.6.7/library/json.html
import json
# http://docs.python.org/release/2.6.7/library/unittest.html
import unittest
# http://docs.python.org/release/2.6.7/library/urllib.html
import urllib

import testbase

class testConsole(testbase.testBase):

    def testUnicodeOutput(self):
        """Should be able to see some unicode output."""
        stuff = self.Execute(
          r"""print u'\N{left-pointing double angle quotation mark}hello'""", language='python')
        output = testbase.console(stuff)
        # Note that left-pointing double angle quotation mark is
        # U+00AB.
        assert u'\xabhello' in output

    def testNotUTF8(self):
        """Should be able to see some output, even when not UTF-8."""
        # Note that the script intentionally prints something
        # that is not a valid UTF-8 stream.
        stuff = self.Execute(r"""print '\xabHello'""")
        output = testbase.console(stuff)
        assert 'Hello' in output

    def testBinaryAssert(self):
        """Should be able to see assert text, even when non UTF-8."""
        stuff = self.Execute(r"""assert '','\xabAsserted\xbb'""")
        output = testbase.exceptions(stuff)
        assert 'Asserted' in output

