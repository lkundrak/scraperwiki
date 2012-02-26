#!/usr/bin/env python
#
"""hardkilllocal.py

Find all lost processes in the system and kill them.  
Necessary when killlocal might have hit errors during execution.
"""

import os

killed_count = 1
while killed_count > 0:
    print "checking none left ..."
    killed_count = 0
    for t in ['twister', 'www/scraperwiki/uml', 'scriptmgr.js']:
        for s in os.popen('ps -Af | grep %s | grep -v "grep "' % t).readlines():
            try:
                print "killing", s.strip()
                os.kill(int(s.split()[1]), 9)
                killed_count += 1
            except OSError, ose:
                pass
                #print "    missing"

print "... all killed"

