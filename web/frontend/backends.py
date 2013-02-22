from registration.backends.default import DefaultBackend
from codewiki.models import Scraper, UserCodeRole
import datetime


standardemailercode = """
# PLEASE READ THIS BEFORE EDITING
#
# This script generates your email alerts, to tell you when your scrapers
# are broken or someone has edited them.
#
# It works by emailing you the output of this script. If you read the code and
# know what you're doing, you can customise it, and make it send other emails
# for other purposes.

import scraperwiki
emaillibrary = scraperwiki.utils.swimport("general-emails-on-scrapers")
subjectline, headerlines, bodylines, footerlines = emaillibrary.EmailMessageParts()
if bodylines:
    print "\\n".join([subjectline] + headerlines + bodylines + footerlines)
"""

def create_emailer_for_user(user, last_run=None):
    if not last_run:
        last_run = datetime.datetime.now()

    title = "%s's Email Alert Scraper" % (user.get_profile().name or user.username)
    scraper = Scraper.objects.create(title=title,
                            short_name="%s.emailer" % user.username,
                            last_run=last_run,
                            language='python',
                            description=title,
                            privacy_status='visible')
    scraper.commit_code(standardemailercode, 'Initial Commit', user)
    scraper.add_user_role(user, 'owner')
    scraper.add_user_role(user, 'email')


class UserWithNameBackend(DefaultBackend):
    def register(self, request, **kwargs):
        user = super(UserWithNameBackend, self).register(request, **kwargs)
        profile = user.get_profile()
        profile.name = kwargs['name']
        profile.messages = 1
        profile.save()

        create_emailer_for_user(user)

        return user
