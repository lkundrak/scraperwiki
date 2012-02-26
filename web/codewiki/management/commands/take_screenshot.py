from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option
from codewiki.models import View, Scraper
from codewiki.management.screenshooter import ScreenShooter
from itertools import chain

import logging
logging.basicConfig()

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--short_name', '-s', dest='short_name',
                        help='Short name of the scraper to run'),
        make_option('--run_scrapers', dest='run_scrapers', action="store_true",
                        help='Should the Scrapers be run?'),
        make_option('--run_views', dest='run_views', action="store_true",
                        help='Should the Views be run?'),
        make_option('--url_prefix', '-u', dest='url_prefix',
                        help='First part of URL which the views are running on, e.g. https://views.scraperwiki.com'),
        make_option('--verbose', dest='verbose', action="store_true",
                        help='Print lots'),
    )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.screenshooter = ScreenShooter()

    def add_screenshots(self, view, sizes, options):
        if options['verbose']:
            print "Adding screenshot of %s" % view.short_name

        for size_name, size_values in sizes.items():
            self.screenshooter.add_shot(url = view.get_screenshot_url(options['url_prefix']), 
                                        filename = view.get_screenshot_filepath(size_name),
                                        size = size_values,
                                        wiki_type=view.wiki_type, 
                                        id=view.id)

    def handle(self, *args, **options):
        """
            Starting to think we should just accept connections here to trigger the screenshooting (in seq)
            rather than trying to find what needs doing. 
        """
        
        if not options['url_prefix']:
            print "You must provide the url_prefix on which the views are running"
            return

        if options['short_name']:
            views = View.objects.filter(short_name=options['short_name']).exclude(privacy_status="deleted")
        elif options['run_views']:
            views = View.objects.filter(has_screen_shot=False).exclude(privacy_status="deleted").order_by("-id")
        else:
            views = []
        if options['verbose']:
            print 'Processing %d views' % ( len(views), )
        
        if options['short_name']:
            scrapers = Scraper.objects.filter(short_name=options['short_name']).exclude(privacy_status="deleted")
        elif options['run_scrapers']:
            scrapers = Scraper.objects.filter(has_screen_shot=False).exclude(privacy_status="deleted").exclude(short_name__endswith='.emailer').order_by("-id")
        else:
            scrapers = []
        if options['verbose']:
            print 'Processing %d scrapers' % ( len(scrapers), )

        for view in views:
            self.add_screenshots(view, settings.VIEW_SCREENSHOT_SIZES, options)

        for scraper in scrapers:
            if not scraper.has_screenshot():
                self.add_screenshots(scraper, settings.SCRAPER_SCREENSHOT_SIZES, options)
            elif options['verbose']:
                print '%s has a screenshot' % (scraper.short_name,)

        if options['verbose']:
            print "------ Starting Screenshooting ------"

        self.screenshooter.run(options['verbose'])
