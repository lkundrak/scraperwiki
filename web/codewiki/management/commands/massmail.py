from django.core.management.base import BaseCommand, CommandError
from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings
from optparse import make_option

from django.contrib.auth.models import User

import os, sys
import logging
logging.basicConfig()

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        # Start after the specified email address
        make_option('--startafter', '-s', dest='startafter', help='The email address to start with'),
        
        # Subject (make sure you quote it on command line)
        make_option('--subject', '-j', dest='subject', help='The subject'),        
        
        # The name of the template, relative from current location, no extension, .html and .txt will be 
        # added automatically
        make_option('--template', '-t', dest='tpl', help='The tpl name path relative to .'),  
        
        # Only send emails to scraperwiki.com addresses and nowhere else.
        make_option('--nosend', '-n', dest='nosend', help='Only send to scraperwiki.com.',action="store_true"),                
    )

    def handle(self, *args, **options):
        """
        Send the mail!!
        """
        if not 'tpl' in options or not options['tpl']:
            print 'You need to specify the name of the .html and .txt file (without extension)'
            sys.exit(1)
        
        # Make sure we can find the files and then load them
        txt = os.path.join( os.getcwd(), options['tpl']) + '.txt'
        html = os.path.join( os.getcwd(), options['tpl']) + '.html'        
        if not os.path.exists(txt) or not os.path.exists(html):
            print "Can't find the text and html files: %s" % txt
            sys.exit(1) 
            
        text_content = open(txt).read()
        html_content = open(html).read()
        
        # Get all active users ordered by email, and check if we are being told to
        # start from a set address
        users = User.objects.filter(is_active=True).order_by('email')
        if 'startat' in options:
            users = users.filter(email__gt=options['startafter'])    
            
        print '*' * 80
        print 'Processing %d users' % users.count()
        print '*' * 80

        c = get_connection()
        subject, from_email = options.get('subject',''), 'ScraperWiki <feedback@scraperwiki.com>'
        for user in users:
            print 'Starting '
            msg = EmailMultiAlternatives(subject, text_content, from_email, [user.email], connection=c)
            msg.attach_alternative(html_content, "text/html")
            if options['nosend'] and not user.email.endswith('@scraperwiki.com'):
                print 'Ignoring %s as nosend was specified' % user.email
                continue
                
            msg.send()            
            print '.. done', user.email        
            
        
        
