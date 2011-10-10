#!/usr/bin/env python

import sys, unittest, imp, optparse, time, traceback
from selenium_test import SeleniumTest
import simplejson as json

# This is a copy of unittest._WritelnDecorator, unittest._TextTestResult, and
# unittest.TextTestRunner, that adds extra option of pausing whenever there is an
# error. 

class _OurWritelnDecorator:
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        return getattr(self.stream,attr)

    def writeln(self, arg=None):
        if arg: self.write(arg)
        self.write('\n') # text-mode streams translate to \r\n if needed


class _OurTextTestResult(unittest.TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by TextTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, descriptions, verbosity, pause_on_failure):
        unittest.TestResult.__init__(self)
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions
        self.pause_on_failure = pause_on_failure

    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
            self.stream.flush()

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    def pauseIfSetTo(self, err):
        if self.pause_on_failure:
            traceback.print_exc(err)
            raw_input("press return to continue >>> ")

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
            self.pauseIfSetTo(err)
        elif self.dots:
            self.stream.write('E')
            self.stream.flush()

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
            self.pauseIfSetTo(err)
        elif self.dots:
            self.stream.write('F')
            self.stream.flush()

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % err)



class OurTextTestRunner:
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1, pause_on_failure=False):
        self.stream = _OurWritelnDecorator(stream)
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.pause_on_failure = pause_on_failure

    def _makeResult(self):
        return _OurTextTestResult(self.stream, self.descriptions, self.verbosity, self.pause_on_failure)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        result.printErrors()
        self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run != 1 and "s" or "", timeTaken))
        self.stream.writeln()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        else:
            self.stream.writeln("OK")
        return result


#   eg:
#
# python selenium_runner.py --url=http://dev.scraperwiki.com --seleniumhost=ondemand.saucelabs.com 
#           --username=goatchurch --accesskey=6727bb66-998e-464c-b8f1-bb4f31d1a531 --os="Windows 2003" 
#           --browser=firefox --browserversion=3.6.--tests=test_scrapers,test_scrapers
#
# ./tests/selenium_runner.py --url=https://dev.scraperwiki.com/ --adminusername=frabcus --adminpassword=XXXXX --pause --verbosity=2

if __name__ == '__main__':
    parser = optparse.OptionParser()

    parser.add_option("-u", "--url", dest="url", action="store", type='string',
                      help="URL of the ScraperWiki web application to test, defaults to http://localhost:8000/",  
                      default="http://localhost:8000/", metavar="application url (string)")

    parser.add_option("--tests", default="test_registration,test_scrapers,test_api", 
                     help="Comma separated list of tests to run, defaults to 'test_registration,test_scrapers'. Each parameter can either be a) a module name, e.g. test_registration, b) a class within a module, e.g. test_registration.TestRegistration, or c) just one test method, e.g. test_registration.TestRegistration.test_invalid_email")
    parser.add_option("--verbosity", dest="verbosity", action="store", default=1, type='int', 
                     help="How much to display while running the tests, try 0, 1, 2. Default is 1.")
    parser.add_option("--pause", dest="pause", action="store_true", default=False, 
                     help="Pause whenever a test fails, so you can look at browser and logs and see what is happening")

    parser.add_option("-s", "--seleniumhost", dest="shost", action="store", type='string',
                      help="The host that Selenium RC is running on",  
                      default="localhost", metavar="selenium host (string)")
    parser.add_option("-p", "--seleniumport", dest="sport", action="store", type='int',
                      help="The port that Selenium RC is running on",  
                      default=4444, metavar="Selenium port")
    parser.add_option("--username", help="Login to Selenium RC, if needed")
    parser.add_option("--accesskey", help="Access control to Selenium RC, if needeed")
    parser.add_option("--os", help="Operating system to run browser on, passed to Selenium RC, optional")
    parser.add_option("--browser", default="*firefox", 
                      help="Which browser, e.g. *firefox, *chrome, *safari, *iexplore. Put in a bad value to see full list. Defaults to *firefox.")
    parser.add_option("--browserversion", help="Passed into selenium with browser parameter, optional")
    parser.add_option("--adminusername", action="store", type="string", default="", dest="adminusername",
                      help="Specify Django admin account username for more complete testing coverage. Requires --adminpassword")
    parser.add_option("--adminpassword", action="store", type="string", default="", dest="adminpassword",
                      help="Specify Django admin account password. Requires --adminusername")

    
    (options, args) = parser.parse_args()
    if len(args) > 0:
        print "No arguments required, just options"
        parser.print_help()
        sys.exit(1)

    if (bool(options.adminusername) ^ bool(options.adminpassword)):
        print "Need --adminusername and --adminpassword"
        parser.print_help()
        sys.exit(1)
    elif (bool(options.adminusername) and bool(options.adminpassword)):
        SeleniumTest._adminuser = {"username":options.adminusername, "password":options.adminpassword}
    else:
        SeleniumTest._adminuser = {}
    
    SeleniumTest._selenium_host = options.shost
    SeleniumTest._selenium_port = options.sport
    SeleniumTest._app_url = options.url
    SeleniumTest._verbosity = options.verbosity
    if options.username and options.accesskey and options.os and options.browser and options.browserversion:
        SeleniumTest._selenium_browser = json.dumps({ "username":options.username, "access-key":options.accesskey, 
                                                      "os":options.os, "browser":options.browser, "browser-version":options.browserversion })
    else:
        SeleniumTest._selenium_browser = options.browser

    if options.verbosity > 1:
        print "SeleniumRC %s:%d, ScraperWiki %s, Browser %s" % (SeleniumTest._selenium_host, SeleniumTest._selenium_port, SeleniumTest._app_url, str(SeleniumTest._selenium_browser))
        if 'localhost' in options.url:
            print '*' * 80
            print 'If running tests locally, make sure that seleniumrc is running along with the\n\
        local services inside the virtualenv'
            print '*' * 80
        
    for testsstring in options.tests.split(","):
        if options.verbosity > 1:
            print '\n%s\nRunning tests: %s\n' % ("="*80,testsstring)
        elif options.verbosity > 0:
            print 'tests %s' % (testsstring)
        loader = unittest.TestLoader().loadTestsFromName( testsstring )
        OurTextTestRunner( verbosity=options.verbosity, pause_on_failure = options.pause ).run( loader )
    
    
    
