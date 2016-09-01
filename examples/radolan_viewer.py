# -*- coding: utf-8 -*-
import sys

try:
    from sip import setapi
    setapi("QVariant", 2)
    setapi("QString", 2)
except ImportError:
    pass


#from PyQt4 import QtGui
from rview import gui

if __name__ == '__main__':
    #print(dir(pentecost))
    gui.start(sys)
