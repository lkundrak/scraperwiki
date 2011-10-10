from django.core.management.base import BaseCommand
from django.db.models import Sum, Max

from kpi.models import DatastoreRecordCount, MonthlyCounts
from codewiki.models import Scraper, Code, View, User

from kpi.views import START_YEAR, one_month_in_the_future

import datetime

class Command(BaseCommand):
    def handle(self, *args, **options):
        # count records in database
        record_count_now = Scraper.objects.aggregate(record_count=Sum('record_count'))['record_count']
        drc = DatastoreRecordCount.objects.get_or_create(date=datetime.date.today(), defaults = {'record_count':  record_count_now})[0]
        drc.record_count = record_count_now
        drc.save()

        # do various monthly statistics
        years_list = []

        for i, year in enumerate(range(START_YEAR, datetime.date.today().year + 1)):
            months_list = []
            for month in range(1, 13):
                month_data = {}
                this_month = datetime.date(year, month, 1)
                next_month = one_month_in_the_future(month, year) 

                month_data['total_scrapers'] = Scraper.objects.filter(created_at__lte=next_month).exclude(privacy_status="deleted").count()
                month_data['this_months_scrapers'] = Scraper.objects.filter(created_at__year=year, created_at__month=month).exclude(privacy_status="deleted").count()
                month_data['total_views'] = View.objects.filter(created_at__lte=next_month).exclude(privacy_status="deleted").count()
                month_data['this_months_views'] = View.objects.filter(created_at__year=year, created_at__month=month).exclude(privacy_status="deleted").count()
                month_data['total_users'] = User.objects.filter(date_joined__lte=next_month).count()
                month_data['this_months_users'] = User.objects.filter(date_joined__year=year, date_joined__month=month).count()

                last_in_month_with_record = DatastoreRecordCount.objects.filter(date__lt=next_month, date__gte=this_month).aggregate(Max('date'))['date__max']
                if last_in_month_with_record:
                    drc = DatastoreRecordCount.objects.get(date=last_in_month_with_record)
                    month_data['datastore_record_count'] = drc.record_count
                else:
                    month_data['datastore_record_count'] = 0

                months_list.append(month_data)

                if next_month > datetime.date.today():
                    # There shouldn't be any data for the future!
                    break
            years_list.append(months_list)
       
        # work out unique active code writers / month ..
        for code in Code.objects.all():
            # don't count editing own emailer for now
            if code.is_emailer():
                continue
            for commitentry in code.get_commit_log("code"):
                # some early scrapers have a servername as user for the first revision, and get no user entry
                if 'user' not in commitentry:
                    continue

                user = commitentry['user']
                when = commitentry['date']

                username = user.username
                year = when.year - START_YEAR
                month = when.month - 1

                if month < 0 or month > 12 or year < 0 or year > datetime.date.today().year - START_YEAR:
                    # print "Ignoring out of date range log entry year %d month %d when %s" % (year, month, str(when))
                    pass
                else:
                    month_data = years_list[year][month]
                    if 'active_coders' not in month_data.keys():
                        month_data['active_coders'] = {}
                    if 'longtime_active_coders' not in month_data.keys():
                        month_data['longtime_active_coders'] = {}
                    month_data['active_coders'][username] = 1
                    # if they joined in a previous month
                    if user.date_joined.date() < datetime.date(when.year, when.month, 1):
                        month_data['longtime_active_coders'][username] = 1
        # ... and count how many entries there are
        last_active_coders = 0
        last_longtime_active_coders = 0
        last_datastore_record_count = 0
        for i, year in enumerate(range(START_YEAR, datetime.date.today().year + 1)):
            for month in range(1, 13):
                month_data = years_list[i][month - 1]

                month_data['active_coders'] = len(month_data.get('active_coders', []))
                month_data['delta_active_coders'] = month_data['active_coders'] - last_active_coders
                last_active_coders = month_data['active_coders']

                month_data['longtime_active_coders'] = len(month_data.get('longtime_active_coders', []))
                month_data['delta_longtime_active_coders'] = month_data['longtime_active_coders'] - last_longtime_active_coders
                last_longtime_active_coders = month_data['longtime_active_coders']

                month_data['delta_datastore_record_count'] = month_data['datastore_record_count'] - last_datastore_record_count
                last_datastore_record_count = month_data['datastore_record_count']
                
                next_month = one_month_in_the_future(month, year) 
                if next_month > datetime.date.today():
                    break

        # save it
        for i, year in enumerate(range(START_YEAR, datetime.date.today().year + 1)):
            for month in range(1, 13):
                month_data = years_list[i][month - 1]
                when = datetime.datetime(year, month, 1) # first of month
                mc = MonthlyCounts.objects.get_or_create(date=when, defaults = month_data)[0]
                mc.delete() # force refresh
                mc = MonthlyCounts.objects.get_or_create(date=when, defaults = month_data)[0]

                next_month = one_month_in_the_future(month, year) 
                if next_month > datetime.date.today():
                    break


