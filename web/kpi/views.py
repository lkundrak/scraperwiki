from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.template import RequestContext
from django.forms.models import model_to_dict

from kpi.models import DatastoreRecordCount, MonthlyCounts
from codewiki.models import Scraper, Code, View

import datetime, calendar

START_YEAR = 2010

def one_month_in_the_future(month, year):
    if month == 12:
        new_month = 1
    else:
        new_month = month + 1
    return datetime.date(year + (month / 12), new_month, 1)

def index(request):
    user = request.user
    context = {}

    if not user.is_authenticated() or not user.is_staff:
        raise PermissionDenied

    years_list = []
    for i, year in enumerate(range(START_YEAR, datetime.date.today().year + 1)):
        months_list = []
        for month in range(1, 13):
            when = datetime.datetime(year, month, 1) # first of month
            next_month = one_month_in_the_future(month, year)

            mc = MonthlyCounts.objects.get(date=when)
            month_data = model_to_dict(mc)
            month_data['month'] = calendar.month_abbr[month]

            months_list.append(month_data)

            if next_month > datetime.date.today():
                break
        years_list.append({'year': year, 'months': months_list, 'offset': i * 12})
    years_list[-1]['months'][-1]['current_month'] = True


    context['data'] = years_list 
    
    return render_to_response('kpi/index.html', context, context_instance = RequestContext(request))
    
