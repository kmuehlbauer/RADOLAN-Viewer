__author__ = 'k.muehlbauer'

# -*- coding: utf-8 -*-

"""
Radar (Radolan) Viewer 0.1

First implementation of radar viewer based on openGL (vispy-package)

# Author: Kai Muehlbauer
"""

import glob
import datetime as dt
import warnings

from PyQt4.QtCore import Qt, QSize, QTimer
from PyQt4.QtGui import QApplication, QWidget, QSlider, QLabel, QBoxLayout, QGridLayout, QFileDialog, QPushButton, \
    QPlainTextEdit, QFont, QHBoxLayout, QVBoxLayout, QToolButton, QStyle

import numpy as np
from vispy import app
from vispy import gloo
from vispy import visuals
from vispy.visuals.transforms import STTransform, TransformSystem

import wradlib as wrl


# function taken from wradlib.io module to load raw data
def read_RADOLAN_composite(fname, missing=-9999, loaddata=True):
    """Read quantitative radar composite format of the German Weather Service

    The quantitative composite format of the DWD (German Weather Service) was
    established in the course of the `RADOLAN project <http://www.dwd.de/RADOLAN>`
    and includes several file types, e.g. RX, RO, RK, RZ, RP, RT, RC, RI, RG, PC,
    PG and many, many more.
    (see format description on the RADOLAN project homepage :cite:`DWD2009`).

    At the moment, the national RADOLAN composite is a 900 x 900 grid with 1 km
    resolution and in polar-stereographic projection. There are other grid resolutions
    for different composites (eg. PC, PG)

    **Beware**: This function already evaluates and applies the so-called PR factor which is
    specified in the header section of the RADOLAN files. The raw values in an RY file
    are in the unit 0.01 mm/5min, while read_RADOLAN_composite returns values
    in mm/5min (i. e. factor 100 higher). The factor is also returned as part of
    attrs dictionary under keyword "precision".

    Parameters
    ----------
    fname : path to the composite file

    missing : value assigned to no-data cells

    Returns
    -------
    output : tuple of two items (data, attrs)
        - data : numpy array of shape (number of rows, number of columns)
        - attrs : dictionary of metadata information from the file header

    """

    NODATA = missing
    mask = 0xFFF  # max value integer

    f = wrl.io.get_radolan_filehandle(fname)

    header = wrl.io.read_radolan_header(f)

    attrs = wrl.io.parse_DWD_quant_composite_header(header)

    if not loaddata:
        f.close()
        return None, attrs

    attrs["nodataflag"] = NODATA

    if not attrs["radarid"] == "10000":
        warnings.warn("WARNING: You are using function e" +
                      "wradlib.io.read_RADOLAN_composit for a non " +
                      "composite file.\n " +
                      "This might work...but please check the validity " +
                      "of the results")

    # read the actual data
    indat = wrl.io.read_radolan_binary_array(f, attrs['datasize'])

    if attrs["producttype"] in ["RX", "EX"]:
        #convert to 8bit integer
        arr = np.frombuffer(indat, np.uint8).astype(np.uint8)
        arr = np.where(arr == 250, 255, arr)
        attrs['cluttermask'] = np.where(arr == 249)[0]

    elif attrs['producttype'] in ["PG", "PC"]:
        arr = wrl.io.decode_radolan_runlength_array(indat, attrs)
    else:
        # convert to 16-bit integers
        arr = np.frombuffer(indat, np.uint16).astype(np.uint16)
        # evaluate bits 13, 14, 15 and 16
        attrs['secondary'] = np.where(arr & 0x1000)[0]
        nodata = np.where(arr & 0x2000)[0]
        negative = np.where(arr & 0x4000)[0]
        attrs['cluttermask'] = np.where(arr & 0x8000)[0]
        # mask out the last 4 bits
        arr = arr & mask
        # consider negative flag if product is RD (differences from adjustment)
        if attrs["producttype"] == "RD":
            # NOT TESTED, YET
            arr[negative] = -arr[negative]
        # apply precision factor
        # this promotes arr to float if precision is float
        #arr = arr * attrs["precision"]
        # set nodata value
        #arr[nodata] = NODATA
        arr[attrs['secondary']] = 4096
        arr[nodata] = 4096

    # anyway, bring it into right shape
    arr = arr.reshape((attrs["nrow"], attrs["ncol"]))

    return arr, attrs

# Colorbar Canvas
class CBarCanvas(app.Canvas):
    def __init__(self):
        app.Canvas.__init__(self, keys='interactive', size=(25, 900))

        # create colorbar data
        self.data = np.flipud(np.repeat(np.arange(0, 900, 1, dtype=np.int16)[:, np.newaxis], 25, 1))

        # create image visual
        self.image = visuals.ImageVisual(self.data, method='auto', cmap='cubehelix', clim=(0, 900))

        # Create a TransformSystem that will tell the visual how to draw
        self.tr_sys = TransformSystem(self)

    def on_draw(self, ev):
        gloo.clear(color='black', depth=True)
        gloo.set_viewport(0, 0, *self.physical_size)
        self.image.draw(self.tr_sys)

# Radar View Canvas
class Canvas(app.Canvas):
    def __init__(self):
        app.Canvas.__init__(self, keys='interactive', size=(900, 900))

        # dummy data (Radolan 900x900)
        self.data = np.zeros((900, 900))

        # create image visual
        self.image = visuals.ImageVisual(self.data, method='auto', cmap='cubehelix', clim='auto')

        # Create a TransformSystem that will tell the visual how to draw
        self.tr_sys = TransformSystem(self)

        self.flist = None
        self.actualFrame = 0
        self.frames = 0

    def on_draw(self, ev):
        gloo.clear(color='black', depth=True)
        gloo.set_viewport(0, 0, *self.physical_size)
        if self.flist:
            self.image.set_data(np.flipud(self.data))
            self.image.draw(self.tr_sys)

# create Widget which holds some printed information
class TextWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self, None)

        self.productTypeLabel = QLabel("Product Type", self)
        self.dateTimeLabel = QLabel("dateTime", self)
        self.radolanVersionLabel = QLabel("Radolan Version", self)
        self.productType = QLabel("Product Type", self)
        self.dateTime = QLabel("Date", self)
        self.radolanVersion = QLabel("Radolan Version", self)

        self.hbox1 = QHBoxLayout()
        self.hbox1.addWidget(self.productTypeLabel)
        self.hbox1.addWidget(self.dateTimeLabel)
        self.hbox1.addWidget(self.radolanVersionLabel)

        self.hbox2 = QHBoxLayout()
        self.hbox2.addWidget(self.productType)
        self.hbox2.addWidget(self.dateTime)
        self.hbox2.addWidget(self.radolanVersion)

        self.attrBox = QVBoxLayout()
        self.attrBox.addLayout(self.hbox1)
        self.attrBox.addLayout(self.hbox2)

        self.setLayout(self.attrBox)

        self.show()

# main Window Widget
class MainWindow(QWidget):
    def __init__(self):
        QWidget.__init__(self, None)

        # initiate timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.reload)

        # layout id gridbox-like
        self.box = QGridLayout()
        self.resize(800, 800)
        self.setLayout(self.box)

        # Create two labels and a button
        self.vertLabel = QLabel("Radolan Data Window", self)
        self.timeLabel = QLabel("Time", self)
        self.sliderLabel = QLabel("00:00", self)

        # File Dialog
        self.dlg = QFileDialog()
        self.dlg.setFileMode(QFileDialog.Directory)
        self.dlg.setOption(QFileDialog.ShowDirsOnly, True)

        # Canvas
        self.canvas = None
        self.cbar = CBarCanvas()

        # Sliders
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setTickInterval(1)
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.slider_moved)

        self.cHighSlider = QSlider(Qt.Horizontal)
        self.cHighSlider.setMinimum(0)
        self.cHighSlider.setMaximum(4096)
        self.cHighSlider.setTickInterval(1)
        self.cHighSlider.setSingleStep(1)
        self.cHighSlider.setValue(4096)
        self.cHighSlider.valueChanged.connect(self.cHighSlider_moved)

        self.cHighLabel = QLabel("Upper Limit:")
        self.cHighValue = QLabel("4096")

        # Load Button
        self.loadButton = QPushButton("Open Directory")
        self.loadButton.clicked.connect(self.button_clicked)

        # Text Output Widget
        self.attrWidget = TextWidget()
        self.attrWidget.setVisible(False)

        self.createButtons()

        # grid parameters
        self.c1 = 0
        self.c2 = 10

        # add Widgets to Layout
        self.box.addWidget(self.loadButton, 0, self.c1, 1, 11)
        self.box.addWidget(self.dlg, 1, self.c1, 3, 11)
        self.box.addWidget(self.attrWidget, 1, self.c1, 3, -1)
        self.box.addWidget(self.vertLabel, 6, self.c1, 1, 10)
        self.box.addWidget(self.cbar.native, 5, self.c2, 10, 1)
        self.box.addWidget(self.timeLabel, 4, self.c1, 1, 10)
        self.box.addWidget(self.playPauseButton, 4, self.c1 + 1, 1, 1)
        self.box.addWidget(self.cHighLabel, 4, self.c1 + 4, 1, 1)
        self.box.addWidget(self.cHighValue, 4, self.c1 + 5, 1, 1)
        self.box.addWidget(self.cHighSlider, 4, self.c1 + 6, 1, 4)
        self.box.addWidget(self.sliderLabel, 5, self.c1, 1, 1)
        self.box.addWidget(self.slider, 5, self.c1 + 1, 1, 9)
        self.show()

        # connect Filedialog
        self.dlg.fileSelected.connect(self.folder_selected)

    def folder_selected(self, folder):
        if not self.canvas:
            self.canvas = Canvas()
            self.box.addWidget(self.canvas.native, 7, self.c1, -1, 10)
        inname = "/raa*"
        self.canvas.flist = sorted(glob.glob(str(folder) + inname))
        self.canvas.frames = len(self.canvas.flist)
        self.slider.setMaximum(self.canvas.frames)
        self.attrWidget.setVisible(True)
        self.slider.setValue(1)
        self.slider_moved(1)

    def button_clicked(self):
        self.attrWidget.setVisible(False)
        self.dlg.setVisible(True)

    # loop continuously through data
    def reload(self):
        if self.slider.value() == self.slider.maximum():
            self.slider.setValue(1)
        else:
            self.slider.setValue(self.slider.value() + 1)

    # changing upper limit
    def cHighSlider_moved(self, position):
        clow, chigh = self.canvas.image.clim
        self.canvas.image.clim = (clow, position)
        self.cHighValue.setText(str(position))

    # slide through data
    def slider_moved(self, position):
        self.canvas.actualFrame = position - 1
        self.canvas.data, self.canvas.attrs = read_RADOLAN_composite(self.canvas.flist[self.canvas.actualFrame],
                                                                     missing=0)
        # adapt color limits
        if self.canvas.data.dtype == 'uint8':
            self.cHighSlider.setMaximum(255)
        else:
            self.cHighSlider.setMaximum(4096)

        # change and update
        self.canvas.update()
        self.sliderLabel.setText(self.canvas.attrs['datetime'].strftime("%H:%M"))
        self.attrWidget.radolanVersion.setText(self.canvas.attrs['radolanversion'])
        self.attrWidget.dateTime.setText(self.canvas.attrs['datetime'].strftime("%Y-%m-%d"))
        self.attrWidget.productType.setText(self.canvas.attrs['producttype'].upper())

    # start/stop capability
    def playpause(self):
        if self.playPauseButton.toolTip() == 'Play':
            self.playPauseButton.setToolTip("Pause")
            self.timer.start()
            self.playPauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playPauseButton.setToolTip("Play")
            self.timer.stop()
            self.playPauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    # create play/pause Button
    def createButtons(self):
        iconSize = QSize(18, 18)

        self.playPauseButton = QToolButton()
        self.playPauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playPauseButton.setIconSize(iconSize)
        self.playPauseButton.setToolTip("Play")
        self.playPauseButton.clicked.connect(self.playpause)

if __name__ == '__main__':
    app.create()
    m = MainWindow()
    app.run()