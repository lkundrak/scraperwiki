from django.utils.log import getLogger
import sys
import os
import logging.handlers
from django.core.exceptions import PermissionDenied

logger = getLogger('django.request')

class ExceptionLoggingMiddleware(object):

    def process_exception(self, request, exception):
        import traceback
        
        # We are not interested in being emailed with no exception
        if not exception:
            return None
            
        logger.error('ExceptionLoggingMiddleware caught: ' + str(exception), exc_info=sys.exc_info())
        return None

# Make log files world writeable, so both Apache and scraperdeploy can write to them
# See: http://stackoverflow.com/questions/1407474/does-python-logging-handlers-rotatingfilehandler-allow-creation-of-a-group-writab
class WorldWriteRotatingFileHandler(logging.handlers.RotatingFileHandler):    
    def _open(self):
        prevumask=os.umask(0o000)
        rtv=logging.handlers.RotatingFileHandler._open(self)
        os.umask(prevumask)
        return rtv


