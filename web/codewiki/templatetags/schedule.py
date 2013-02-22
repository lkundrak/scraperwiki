from django.template import Library
from django.template.defaultfilters import stringfilter
from codewiki.models.scraper import SCHEDULE_OPTIONS

register = Library()

@stringfilter
def schedule(value):
    for schedule_option in SCHEDULE_OPTIONS:
        if schedule_option[0] == int(value):
            return schedule_option[3]
    return "Runs every " + str(int(value)) + " seconds"

register.filter(schedule)
