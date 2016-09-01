# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016, wradlib Development Team. All Rights Reserved.
# Distributed under the MIT License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
#!/usr/bin/env python

"""
"""

import os
import glob
import netCDF4 as nc

from vispy.color.colormap import get_colormaps
from vispy import color

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QApplication,\
                        QLabel,\
                        QFontMetrics,\
                        QPainter

import wradlib as wrl

# other pentecost_qt imports
from rview import utils

def get_radolan_variable(filename):
    return wrl.io.read_RADOLAN_composite(filename)

class LongLabel(QLabel):
    def paintEvent( self, event ):
        painter = QPainter(self)

        metrics = QFontMetrics(self.font())
        elided  = metrics.elidedText(self.text(), QtCore.Qt.ElideLeft, self.width())

        painter.drawText(self.rect(), self.alignment(), elided)

# Properties
class PropertiesWidget(QtGui.QWidget):
    """
    Widget for editing OBJECT parameters
    """
    signal_object_changed = QtCore.pyqtSignal(name='objectChanged')
    signal_slider_changed = QtCore.pyqtSignal(name='slidervalueChanged')
    signal_speed_changed = QtCore.pyqtSignal(name='speedChanged')
    signal_playpause_changed = QtCore.pyqtSignal(name='startstop')
    signal_toggle_Cursor = QtCore.pyqtSignal(name='toggleCursor')
    signal_data_changed = QtCore.pyqtSignal(name='data_changed')

    def __init__(self, parent=None):
        super(PropertiesWidget, self).__init__(parent)

        l_cmap = QtGui.QLabel("Colormap")
        self.cmap = list(get_colormaps().keys())
        #print(self.cmap)
        self.combo = QtGui.QComboBox(self)
        self.combo.addItems(self.cmap)
        self.combo.setCurrentIndex(self.combo.count() - 1)
        self.combo.currentIndexChanged.connect(self.update_param)

        self.curCheckBox = QtGui.QCheckBox()
        self.curCheckBox.stateChanged.connect(self.toggleCursor)
        self.curSelectLabel = QtGui.QLabel("Cursor Activation", self)

        # HLine
        self.hline0 = QtGui.QFrame()
        self.hline0.setFrameShape(QtGui.QFrame.HLine)
        self.hline0.setFrameShadow(QtGui.QFrame.Sunken)

        # Start Directory
        self.dirname = "/automount/radar/dwd/rx/2014/2014-06/2014-06-08/"
        self.dirLabel = LongLabel(self.dirname)
        self.filelist = sorted(glob.glob(os.path.join(self.dirname, "raa01*")))
        self.frames = len(self.filelist)
        self.actualFrame = 0

        attrs, meta = wrl.io.read_RADOLAN_composite(self.filelist[0])
        self.data0ranges =[(0,100)]

        self.data0ComboBox = QtGui.QComboBox()
        self.data0ComboBox.addItem(meta['producttype'])
        self.data0ComboBox.setCurrentIndex(0)
        self.data0ComboBox.currentIndexChanged.connect(self.update_data)

        # Sliders
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(self.frames)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.update_slider)
        self.dateLabel = QtGui.QLabel("Date", self)
        self.date = QtGui.QLabel("1900-01-01", self)
        self.timeLabel = QtGui.QLabel("Time", self)
        self.sliderLabel = QtGui.QLabel("00:00", self)

        # Button
        self.createButton()

        # SpeedSlider
        self.speed = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.speed.setMinimum(0)
        self.speed.setMaximum(1000)
        self.speed.setTickInterval(10)
        self.speed.setSingleStep(10)
        self.speed.valueChanged.connect(self.speed_changed)

        self.gbox1 = QtGui.QGridLayout()
        self.srcbox = QtGui.QGridLayout()
        mbox = QtGui.QGridLayout()
        gbox2 = QtGui.QGridLayout()

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(self.gbox1)
        vbox.addLayout(self.srcbox)
        vbox.addLayout(mbox)
        vbox.addLayout(gbox2)
        vbox.addStretch(0)

        # Misc Properties
        self.gbox1.addWidget(l_cmap, 0, 0)
        self.gbox1.addWidget(self.combo, 0, 2)
        self.gbox1.addWidget(self.curCheckBox,3,1)
        self.gbox1.addWidget(self.curSelectLabel,3,0)
        self.gbox1.addWidget(self.hline0,7,0,1,3)

        # Data Source Control
        self.srcbox.addWidget(self.dirLabel, 0, 1)
        self.dirLabel.setFixedSize(220,14)
        self.srcbox.addWidget(self.dirButton, 0, 0)
        self.srcbox.addWidget(self.data0ComboBox, 1, 1)

        # Media Control
        mbox.addWidget(self.dateLabel,0,0)
        mbox.addWidget(self.date,0,4)
        mbox.addWidget(self.timeLabel,1,0)
        mbox.addWidget(self.sliderLabel,1,4)
        mbox.addWidget(self.playPauseButton, 2,0)
        mbox.addWidget(self.fwdButton, 2,2)
        mbox.addWidget(self.rewButton, 2,1)
        mbox.addWidget(self.slider,2,3,1,4)
        mbox.addWidget(self.speed,3,0,1,7)

        # Mouse Properties
        # HLine
        self.hline = QtGui.QFrame()
        self.hline.setFrameShape(QtGui.QFrame.HLine)
        self.hline.setFrameShadow(QtGui.QFrame.Sunken)
        radolan = wrl.georef.get_radolan_grid()
        self.r0 = radolan[0,0]
        self.mousePointLabel = QtGui.QLabel("Mouse Position", self)
        self.mousePointXYLabel = QtGui.QLabel("XY", self)
        self.mousePointLLLabel = QtGui.QLabel("LL", self)
        self.mousePointXY = QtGui.QLabel("", self)
        self.mousePointLL = QtGui.QLabel("", self)

        gbox2.addWidget(self.hline,0,0,1,3)
        gbox2.addWidget(self.mousePointLabel,1,0)
        gbox2.addWidget(self.mousePointXYLabel,1,1)
        gbox2.addWidget(self.mousePointXY,1,2)
        gbox2.addWidget(self.mousePointLLLabel,2,1)
        gbox2.addWidget(self.mousePointLL,2,2)

        self.hline1 = QtGui.QFrame()
        self.hline1.setFrameShape(QtGui.QFrame.HLine)
        self.hline1.setFrameShadow(QtGui.QFrame.Sunken)

        self.setLayout(vbox)

    def update_data(self):
        self.signal_data_changed.emit()

    def toggleCursor(self):
        self.signal_toggle_Cursor.emit()

    def update_slider(self, position):
        self.actualFrame = position - 1
        self.signal_slider_changed.emit()

    def speed_changed(self, position):
        self.signal_speed_changed.emit()

    def update_param(self, option):
        self.signal_object_changed.emit()

    def createButton(self):
        iconSize = QtCore.QSize(18, 18)

        self.dirButton = QtGui.QToolButton()
        self.dirButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_DirHomeIcon))
        self.dirButton.setIconSize(iconSize)
        self.dirButton.setToolTip("Load Directory")
        self.dirButton.clicked.connect(self.selectDir)

        self.playPauseButton = QtGui.QToolButton()
        self.playPauseButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_MediaPlay))
        self.playPauseButton.setIconSize(iconSize)
        self.playPauseButton.setToolTip("Play")
        self.playPauseButton.clicked.connect(self.playpause)

        self.fwdButton = QtGui.QToolButton()
        self.fwdButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_MediaSeekForward))
        self.fwdButton.setIconSize(iconSize)
        self.fwdButton.setToolTip("SeekForward")
        self.fwdButton.clicked.connect(self.seekforward)

        self.rewButton = QtGui.QToolButton()
        self.rewButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_MediaSeekBackward))
        self.rewButton.setIconSize(iconSize)
        self.rewButton.setToolTip("SeekBackward")
        self.rewButton.clicked.connect(self.seekbackward)

    def selectDir(self):
        f = QtGui.QFileDialog.getExistingDirectory(self, "Select a Folder", "/automount/data/radar/dwd", QtGui.QFileDialog.ShowDirsOnly)

        if os.path.isdir(f):
            self.dirLabel.setText(f)
            self.dirname = f
            self.filelist = glob.glob(os.path.join(self.dirname, "raa01*"))
            data, meta = utils.read_radolan(self.filelist[0])
            print("Meta:", meta)
            self.data0ComboBox.clear()
            self.data0ComboBox.addItem(meta['producttype'])
            self.data0ComboBox.setCurrentIndex(0)

    def seekforward(self):
        if self.slider.value() == self.slider.maximum():
            self.slider.setValue(1)
        else:
            self.slider.setValue(self.slider.value() + 1)
        self.update_slider(self.slider.value())

    def seekbackward(self):
        #print(self.slider.value())
        if self.slider.value() == 1:
            self.slider.setValue(self.slider.maximum())
            self.update_slider(self.slider.maximum())
        else:
            self.slider.setValue(self.slider.value() - 1)
            self.update_slider(self.slider.value() - 1)

    def playpause(self):
        if self.playPauseButton.toolTip() == 'Play':
            self.playPauseButton.setToolTip("Pause")
            #self.timer.start()
            self.playPauseButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_MediaPause))
        else:
            self.playPauseButton.setToolTip("Play")
            #self.timer.stop()
            self.playPauseButton.setIcon(self.style().standardIcon(QtGui.QStyle.SP_MediaPlay))
        self.signal_playpause_changed.emit()

    def show_mouse(self, point):
        self.mousePointXY.setText("({0:d}, {1:d})".format(int(point[0]), int(point[1])))
        ll = utils.radolan_to_wgs84(point + self.r0)
        self.mousePointLL.setText("({0:.1f}, {1:.1f})".format(ll[0], ll[1]))
