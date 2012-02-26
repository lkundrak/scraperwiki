# For using WSGI for development, includes use of "monitor" which watches
# for changes in files and causes restarting.
#
# You'll probably want to copy this file to YOURNAME.wsgi and edit paths.

import sys
import site
import os


root_path = '/Users/francis/code/scraperwiki/'

vepath = root_path + 'lib/python2.7/site-packages'

prev_sys_path = list(sys.path)
# add the site-packages of our virtualenv as a site dir
site.addsitedir(vepath)
# add the app's directory to the PYTHONPATH
sys.path.append(root_path)
sys.path.append(root_path + 'web')

# reorder sys.path so new directories from the addsitedir show up first
new_sys_path = [p for p in sys.path if p not in prev_sys_path]
for item in new_sys_path:
    sys.path.remove(item)
sys.path[:0] = new_sys_path

sys.stdout = sys.stderr
print >> sys.stderr, sys.path


# http://code.google.com/p/modwsgi/wiki/ReloadingSourceCode
import monitor
monitor.start(interval=1.0)
monitor.track(os.path.join(os.path.dirname(__file__), 'web/settings.py'))
monitor.track(os.path.join(os.path.dirname(__file__), 'web/global_settings.py'))



# import from down here to pull in possible virtualenv django install
from django.core.handlers.wsgi import WSGIHandler
os.environ['DJANGO_SETTINGS_MODULE'] = 'web.settings'
application = WSGIHandler()
