from django.db import models

class DatastoreRecordCount(models.Model):
    date = models.DateField(primary_key=True) # just keep one from each day

    record_count = models.IntegerField()

    def __unicode__(self):
        return u"%s - %d records" % (self.date, self.record_count)

class MonthlyCounts(models.Model):
    date = models.DateField(primary_key=True) # first of the month

    total_scrapers = models.IntegerField()
    this_months_scrapers = models.IntegerField()

    total_views = models.IntegerField()
    this_months_views = models.IntegerField()

    total_users = models.IntegerField()
    this_months_users = models.IntegerField()

    active_coders = models.IntegerField()
    delta_active_coders = models.IntegerField()

    longtime_active_coders = models.IntegerField()
    delta_longtime_active_coders = models.IntegerField()

    # these two are a cache - update_kpis fills them in from calculation on DatastoreRecordCount above
    datastore_record_count = models.IntegerField()
    delta_datastore_record_count = models.IntegerField()


