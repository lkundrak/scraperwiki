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
        count = 1
        for shot in self.shots:
            if self.verbose:
                print "%d: Taking screenshot %s" % (count,shot['filename'],)
                print shot['url']
                print _memsize()
            try:
                image = self._get_renderer(shot['size'][0], shot['size'][1]).render(shot['url'])
                if self.verbose:
                    print 'Got Renderered image, saving'
                image.save(shot['filename'], 'png')
                                    
                # TODO:
                # Notify via HTTP that shot['wiki_type'] with id shot['id'] now has an image
                # - Maybe we should post the image?
            except RuntimeError:
                print "Timeout screenshooting %s" % shot['url']
            count = count + 1
        sys.exit(0)

    def add_shot(self, url, filename, size, wiki_type, id):
        if self.verbose:
            print 'Adding ', url
        self.shots.append({'url': url, 'filename': filename, 'size': size, 'wiki_type': wiki_type, 'id':id})
        
    def run(self, verbose=False):
        self.verbose = verbose
        QTimer().singleShot(0, self.__take_screenshots)
        self.app.exec_()

if __name__ == '__main__':
    s = ScreenShooter()
    print 'Adding shots'
    s.add_shot('http://google.com', 'google.png', (200, 200))
    s.add_shot('http://amazon.com', 'amazon.png', (200, 200))
    s.run(verbose=True)
