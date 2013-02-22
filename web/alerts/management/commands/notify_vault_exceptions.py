'''
This is the function that the cronjob should call
for sending vault exception alerts.

:: Testing

Create a database with a bunch of the data.
Or maybe just include this test in the updater script.

'''

from django.core.management.base import BaseCommand, CommandError

from codewiki.models.vault import Vault
from alerts.views import alert_vault_members_of_exceptions

class Command(BaseCommand):
    help = 'Check for exceptions in vaults and send emails to editors.'

    def handle(self, *args, **options):
        for vault in Vault.objects.all():
            alert_vault_members_of_exceptions(vault)
        #self.stdout.write('Done\n')
