#!/usr/bin/env python
# ScraperWiki Limited
# David Jones, 2011-11-29

"""
cleanfd.py command [args ...]

Execs the *command* with the *args* specified, having cleaned the file
descriptor table prior to the exec.  Note that this command does not
return itself, but the exec'd command will return.

All FDs from 3 to SC_OPEN_MAX (which is 1024 on Linux) are closed.
"""

import os
import sys

# http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way/
OPEN_MAX = os.sysconf("SC_OPEN_MAX")

def closefd(arg):
    """Closes the FDs and run the command in the list arg."""

    for i in range(3,OPEN_MAX):
        try:
            os.close(i)
        except OSError:
            # We expect most of close() calls to generate this error
            # (the FD was never open).
            pass

    e = os.execvp(arg[0], arg)
    # Only gets here when it couldn't exec (for example, can't find
    # file).
    print "Couldn't exec %r: %s" % (arg, e)
    return 4

def main(argv=None):
    if argv is None:
        argv = sys.argv

    return closefd(argv[1:])

if __name__ == '__main__':
    sys.exit(main())
