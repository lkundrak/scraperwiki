from django.core.management import call_command 

call_command('flush', interactive=False)
call_command('loaddata', 'test-fixture.yaml')
