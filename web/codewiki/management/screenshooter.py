#!/usr/bin/env python

from webkit2png import WebkitRenderer
from PyQt4.QtGui import QApplication
from PyQt4.QtCore import QTimer, Qt
from PyQt4.QtWebKit import QWebSettings
import sys, signal, gc, os

def _memsize():
    """ this function tries to return a measurement of how much memory
    this process is consuming, in some arbitrary unit (if it doesn't
    manage to, it returns 0).
    """
    gc.collect()
    try:
        x = int(os.popen('ps -p %d -o vsz|tail -1' % os.getpid()).read())
    except:
        x = 0
    return x

class ScreenShooter(object):
    def __init__(self):
        self.app = QApplication([])
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.shots = []
        self.renderers = {}
        self.verbose = False

    def _get_renderer(self, width, height):
        try:
            return self.renderers[(width, height)]
        except:
            renderer = WebkitRenderer(scaleRatio='crop', 
                                      scaleTransform='smooth', 
                                      scaleToWidth=width, 
                                      scaleToHeight=height,
                                      width=1440,
                                      height=900,
                                      wait=5,
                                      timeout=60,
                                      ignoreAlerts=True,
                                      ignoreConfirms=True,
                                      ignoreConsoleMessages=True)
            renderer.qWebSettings[QWebSettings.JavascriptEnabled] = True
            self.renderers[(width, height)] = renderer
            return renderer
        
    def __take_screenshots(self):
        for shot in self.shots:
            if self.verbose:
                print "Taking screenshot %s" % shot['filename']
                print shot['url']
                print _memsize()
            try:
                image = self._get_renderer(shot['size'][0], shot['size'][1]).render(shot['url'])
                image.save(shot['filename'], 'png')
            except RuntimeError:
                print "Timeout screenshooting %s" % shot['url']
        sys.exit(0)

    def add_shot(self, url, filename, size):
        self.shots.append({'url': url, 'filename': filename, 'size': size})
        
    def run(self, verbose=False):
        self.verbose = verbose
        QTimer().singleShot(0, self.__take_screenshots)
        self.app.exec_()

if __name__ == '__main__':
    s = ScreenShooter()
    s.add_shot('http://google.com', 'google.png', (200, 200))
    s.add_shot('http://amazon.com', 'amazon.png', (200, 200))
    s.run()
