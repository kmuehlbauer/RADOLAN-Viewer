# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016, wradlib Development Team. All Rights Reserved.
# Distributed under the MIT License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
#!/usr/bin/env python

import glob
import time
import numpy as np
import datetime as dt
#import matplotlib
#matplotlib.use('Qt4Agg')

from PyQt4 import QtGui, QtCore

# other pentecost_qt imports
from rview.glcanvas import RadolanCanvas
from rview.properties import PropertiesWidget
from rview import utils


class MainWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.resize(600, 500)
        self.setWindowTitle('RADOLAN Viewer')
        self._need_canvas_refresh = False

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.reload)

        splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)

        self.canvas = RadolanCanvas()
        self.canvas.create_native()
        self.canvas.native.setParent(self)
        self.canvas.mouse_moved.connect(self.mouse_moved)

        self.props = PropertiesWidget()
        splitter.addWidget(self.props)
        splitter.addWidget(self.canvas.native)

        self.setCentralWidget(splitter)
        self.props.signal_object_changed.connect(self.update_view)
        self.props.signal_slider_changed.connect(self.slider_changed)
        self.props.signal_playpause_changed.connect(self.start_stop)
        self.props.signal_speed_changed.connect(self.speed)
        self.props.signal_toggle_Cursor.connect(self.toggle_Cursor)
        self.props.signal_data_changed.connect(self.data_changed)
        self.update_view()
        self.slider_changed()
        self._need_recompute = False

    def toggle_Cursor(self):
        isCheck = self.props.curCheckBox.isChecked()
        self.canvas.hline.visible = isCheck
        self.canvas.vline.visible = isCheck
        self.canvas.cursor_text.visible = isCheck
        self.update_canvas()

    def data_changed(self):
        self.canvas.image.clim = 'auto'
        self.canvas.image.update()

        self.update_canvas()
        #self.canvas.cbar.clim = (0, 100)

    def update_view(self):
        print("CMAP:", self.props.combo.currentText())
        #self.canvas.set_colormap(self.props.combo.currentText())
        self.canvas.update()

    def reload(self):
        if self._need_canvas_refresh:
            self._need_canvas_refresh = False
            self.redraw_canvas()
        if self.props.slider.value() == self.props.slider.maximum():
            self.props.slider.setValue(1)
        else:
            self.props.slider.setValue(self.props.slider.value() + 1)

    def start_stop(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()

    def speed(self):
        self.timer.setInterval(self.props.speed.value())

    # slide through data
    def slider_changed(self):
        data, meta = utils.read_radolan(self.props.filelist[self.props.actualFrame], loaddata=False)
        print("Slider-Meta:", meta['datetime'])
        scantime = meta['datetime']
        self.props.sliderLabel.setText(scantime.strftime("%H:%M"))
        self.props.date.setText(scantime.strftime("%Y-%m-%d"))
        self.update_canvas()

    def redraw_canvas(self):
        self.canvas.update()

    def update_canvas(self):

        if self.canvas.image.visible:

            self.data, self.metadata = utils.read_radolan(self.props.filelist[self.props.actualFrame])
            print(self.data.min(), self.data.max())
            def scale(val, src, dst):
                """
                Scale the given value from the scale of src to the scale of dst.
                """
                return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

            #self.canvas.image.set_data(scale(self.data, (0,65), (0,255)))
            self.canvas.image.set_data(self.data)

        self.canvas.update()

    def mouse_moved(self, event):
        self.props.show_mouse(self.canvas._mouse_position)

def start(arg):

    print(arg.argv)
    appQt = QtGui.QApplication(arg.argv)
    win = MainWindow()
    win.show()
    appQt.exec_()

if __name__ == '__main__':
    print('pentecost: Calling module <app> as main...')
