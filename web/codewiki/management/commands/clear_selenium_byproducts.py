from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from codewiki.models import Scraper, View

class Command(BaseCommand):
    def handle(self, **options):
        User.objects.filter(username__regex='^se_test_.{8}_.{4}_.{4}_.{3}$').delete()
        Scraper.objects.filter(short_name__regex='^se_test_.{8}_.{4}_.{4}_.{3}').delete()
        View.objects.filter(short_name__regex='^se_test_.{8}_.{4}_.{4}_.{3}').delete()
