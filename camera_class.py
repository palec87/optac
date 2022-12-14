#!/usr/bin/env python
"""
Classes for acquisition cameras.
1. Sky Basic
2. Virtual
TODO Think about making cameras children of camera class
because of bilerplate code and minimal required parameters
for camera init
"""

import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
import cv2
from threading_class import Get_radon
import time

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


# TODO need to implement camera shutdown
# TODO if it can do hardware binning, implement it, otherwise only software one
# TODO no software binning yet
class Sky_basic(QObject):
    def __init__(self, channel, col_ch, resolution, bin_factor) -> None:
        super(QObject, self).__init__()
        self.channel = channel  # which video input to use (typically 1 or 2)
        self.res = resolution  # tuple (1280,720)
        self.binning_factor = bin_factor  # not sure it can do hardware binning
        self.accum = False
        self.col_ch = col_ch
        self.initialize()

    def initialize(self):
        """initialize cv2 video capture stream"""
        self.capture = cv2.VideoCapture(1)

    def set_average(self, num):
        """Set how many captures are averaged into
        single frame
        """
        self.average = num

    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, int)

    @pyqtSlot()
    def acquire(self):
        """Acquire 3D matrix of the data to be averaged
        into the single frame. In addition counts how
        many times no data were retrieved from the camera.
        """
        self.frame = np.zeros((self.average, self.res[1], self.res[0]),
                              dtype=np.dtype(np.int16))
        no_data_count = 0
        for i in range(self.average):
            ret, frame = self.capture.read()
            if not ret:
                no_data_count += 1
                continue
                # raise RuntimeWarning
            # convert to monochrome and save to self.frame
            if self.col_ch == 3:
                self.frame[i, :] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                # retrieving only one channel
                self.frame[i, :] = frame[:, :, self.col_ch]
        self.construct_data()
        self.data_ready.emit(self.data_avg, no_data_count)
        return

    def construct_data(self):
        """
        sum or mean over the averaged frames, depending if the
        shots are getting accumulated or averaged, respectively.
        """
        if self.accum:
            self.data_avg = np.rot90(np.sum(self.frame, axis=0))
        else:
            self.data_avg = np.rot90(np.mean(self.frame, axis=0))
    _exit = pyqtSignal()

    @pyqtSlot()
    def exit(self):
        """ Try to release the capture port of
        the camera
        """
        try:
            self.capture.release()
            time.sleep(0.5)
        except Exception as e:
            print(f'Camera closing problem: {e}')
            return e


class Virtual(QObject):
    def __init__(self, resolution=128, bin_factor=1) -> None:
        super(QObject, self).__init__()
        self.size = resolution  # int
        self.idx = 0
        self.binning_factor = bin_factor  # not sure it can do hardware binning
        self.accum = False
        self.thread = QThread(parent=self)
        self.radon = Get_radon(self.size)
        self.radon.moveToThread(self.thread)
        # self.thread.started.connect(self.radon.loading_message)
        self.thread.started.connect(self.radon.get_sinogram)
        self.radon.finished.connect(self.sino)
        self.radon.finished.connect(self.thread.quit)
        # self.radon.finished.connect(self.radon.deleteLater)
        self.thread.finished.connect(self.thread.quit)
        self.radon.progress.connect(self.report_progress)
        self.thread.start()

    def sino(self, data):
        """Setting sinogram variable of phantom
        data

        Args:
            data (np.ndarray):  Sinogram of 3D phantom
        """
        print('setting sino variable')
        self.sinogram = data
        # self.thread.quit()

    def report_progress(self, n):
        """Report progress
        TODO to the progress bar
        of the phantom sinogram generation

        Args:
            n (int): percent of progress
        """
        pass
        # print(n)

    # boilerplate code here
    # create super Camera class
    def set_average(self, num):
        """Set how many captures are averaged into
        single frame
        """
        self.average = num

    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, int)

    @pyqtSlot()
    def acquire(self):
        """Simulates acquisition of 3D phantom data
        as if in the experiment, each frame is rotation
        of the phantom by 360/ size of the sinogram"""
        self.frame = np.zeros((self.average, self.size, self.size),
                              dtype=np.dtype(np.int16))
        # for the case of aquiring more frames than sinogram size
        idx_modulo = self.idx % self.size
        for i in range(self.average):
            self.frame[i, :] = self.sinogram[:, :, idx_modulo]
            time.sleep(0.01)

        self.construct_data()
        self.data_ready.emit(self.data_avg, 0)

    # also boilerplate, but in some cases data needs
    # to be rotated 90deg (identify by shape!!)
    def construct_data(self):
        """
        sum or mean over the averaged frames, depending if the
        shots are getting accumulated or averaged, respectively.
        """
        if self.accum:
            self.data_avg = np.sum(self.frame, axis=0)
        else:
            self.data_avg = np.mean(self.frame, axis=0)

    _exit = pyqtSignal()

    @pyqtSlot()
    def exit(self):
        return
