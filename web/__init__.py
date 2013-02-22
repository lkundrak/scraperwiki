# note all example data should have IDs over 10000
def load_data():
	print "This is where the code to load data is gonna sit."
	clear_out_data()
	import_user_data()
	
def import_user_data():
	import_fixture('fixtures/users_fixture.json')
	
def clear_out_data():
	print "Routine to clear out old example data"
	
def import_fixture(fixture_name):
	from django.core import management
	management.call_command('loaddata', fixture_name, verbosity=1)
	print "Imported Fixture %s" % (fixture_name)
	