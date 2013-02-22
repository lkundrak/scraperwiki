#!/usr/bin/python
import os, sys

instance_dir = '/var/www/scraperwiki/'

def createDaemon():
   try:
      pid = os.fork()
   except OSError, e:
      raise Exception, "%s [%d]" % (e.strerror, e.errno)

   if (pid == 0):	# The first child.
      os.setsid()

      try:
         pid = os.fork()	# Fork a second child.
      except OSError, e:
         raise Exception, "%s [%d]" % (e.strerror, e.errno)

      if (pid == 0):	# The second child.
         os.chdir(instance_dir)
         os.umask(0)
      else:
         os._exit(0)
   else:
      os._exit(0)	# Exit parent of the first child.

   import resource		# Resource usage information.
   maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
   if (maxfd == resource.RLIM_INFINITY):
      maxfd = 1024
  
   # Iterate through and close all file descriptors.
   for fd in range(0, maxfd):
      try:
         os.close(fd)
      except OSError:	# ERROR, fd wasn't open to begin with (ignored)
         pass

   os.open("/dev/null", os.O_RDWR)	# standard input (0)

   # Duplicate standard input to standard output and standard error.
   os.dup2(0, 1)			# standard output (1)
   os.dup2(0, 2)			# standard error (2)

   return(0)
   

if __name__ == '__main__':
    createDaemon()
    os.environ['WEBSTORE_SETTINGS'] = sys.argv[1]
    pyenv_bin_dir = os.path.join(instance_dir, 'bin')
    activate_this = os.path.join(pyenv_bin_dir, 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

    from webstore.web import app as application
    application.debug = False 
    application.run( '0.0.0.0', 5000 )
