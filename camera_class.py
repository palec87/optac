#!/usr/bin/env python
"""
Classes for acquisition cameras.

Camera class is a parent class to all the 'real' cameras.
Virtual camera is a separate class.

1. Sky Basic
2. Virtual
3. Phonefix
4. DMK 37BUX252
"""

import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
import cv2
from optac.threading_class import Get_radon
import time

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


class Camera(QObject):
    """
    Parent class to all real acquisition cameras using USB.

    Args:
        QObject (_type_): inherits from base class
        port (int): camera serial port
        channel (str): red, gree, blue, mono
        res (tuple): resolution (rows, columns)
    """
    def __init__(self, port, channel, res) -> None:
        super(QObject, self).__init__()
        self.port = port  # video port to use (typically 1 or 2)
        self.channel = channel  # selecting RGB channels separately
        self.res = res  # tuple (1280,720)
        # self.binning_factor = bin_factor  # not implemented yet
        self.accum = False  # accumulation of frames instead of averaging
        self.rotate = False  # if the output array should be rotated by 90 deg
        self.initialize()

    def initialize(self):
        """
        Initialize cv2 video capture stream. This method
        tries to force resolution of the receiving stream from
        the known channel.
        """
        self.capture = cv2.VideoCapture(
            self.port,
            apiPreference=cv2.CAP_ANY,
            params=[
                cv2.CAP_PROP_FRAME_WIDTH, self.res[0],
                cv2.CAP_PROP_FRAME_HEIGHT, self.res[1],
                ],
            )

    def set_average(self, num):
        """
        How many captures are averaged into a single frame.

        Args:
            num (int): Number of averages
        """
        self.average = num

    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, int)

    @pyqtSlot()
    def acquire(self):
        """
        Acquire Frames in the shape of 3D Matrix
        which gets averaged into single frame.

        pyqtSlot of the acquire thread of the main GUI

        In addition counts how many times no data were retrieved
        from the camera.

        Returns:
            pyqtSignal:
                tuple
                    ndarray of averaged frames
                    int of no data received count
        """
        # preallocation
        self.frame = np.zeros((self.average, self.res[1], self.res[0]),
                              dtype=np.dtype(np.int16))
        no_data_count = 0

        for i in range(self.average):
            ret, frame = self.capture.read()

            # no data received from camera
            if not ret:
                no_data_count += 1
                continue

            # monochrome option should be 0
            if self.channel == 3:
                self.frame[i, :] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:  # retrieve only one channel in case of RGB camera
                self.frame[i, :] = frame[:, :, self.channel]
        self.construct_data()
        self.data_ready.emit(self.data_avg, no_data_count)
        return

    def construct_data(self):
        """
        Construct data from the 3D array from
        :fun:`~Camera.acquire`

        Default is to average data and returns intX array
        (depending on the camera dynamic range). If accumulation
        is selected in the GUI, sum is applied over the acquired
        ndarray. Therefore it can result in larger files.
        """
        if self.accum:
            self.data_avg = np.sum(self.frame, axis=0)
        else:
            self.data_avg = np.mean(self.frame, axis=0)

        if self.rotate:
            self.data_avg = np.rot90(self.data_avg)

    _exit = pyqtSignal()

    @pyqtSlot()
    def exit(self):
        """
        Release the capture port of the camera,
        otherwise raise an exception
        """
        try:
            self.capture.release()
            time.sleep(0.5)
        except Exception as e:
            print(f'Camera closing problem: {e}')
            return e


class Dmk(QObject):
    """Very basic USB camera which can work in
    also with a cell phone via wifi.

    Args:
        QObject (_type_): Base class of the Qt.
    """
    def __init__(self, channel, col_ch, res, bin_factor) -> None:
        super().__init__(channel, col_ch, res)


class Basic_usb(Camera):
    """Very basic USB camera which includes Sky basic or phonefix
    cameras.

    Args:
        QObject (_type_): Base class of the Qt.
        port (int): camera serial port
        channel (str): red, gree, blue, mono
        res (tuple): resolution (rows, columns)
    """
    def __init__(self, port, channel, res) -> None:
        super().__init__(port, channel, res)


class Phonefix(Camera):
    """
    Phonefix HDMI/VGA camera type. For this camera,
    acquisition card is needed, such as capture cards for PC
    gaming.

    Args:
        Camera (QObject): parent class with all the main camera
        functionality
    """
    def __init__(self, channel, col_ch, res):
        # super(self).__init__()
        super().__init__(channel, col_ch, res)

    # if any methods need to be redefined, do it here


# TODO need to implement camera shutdown
# TODO if it can do hardware binning, implement it, otherwise only software one
# TODO no software binning yet

# TODO: refactor as a child of Camera class
class Sky_basic(QObject):
    """Very basic USB camera which can work in
    also with a cell phone via wifi.

    Args:
        QObject (_type_): Base class of the Qt.
    """
    def __init__(self, channel, col_ch, res, bin_factor) -> None:
        super().__init__(channel, col_ch, res)
    #     super(QObject, self).__init__()  # init of the parent class
    #     self.channel = channel  # video port to use (typically 1 or 2)
    #     self.res = resolution  # tuple (1280,720)
    #     self.binning_factor = bin_factor  # not implemented yet
    #     self.accum = False  # accumulation of frames instead of averaging
    #     self.col_ch = col_ch  # selecting RGB channels separately
    #     self.initialize()

    # def initialize(self):
    #     """initialize cv2 video capture stream"""
    #     self.capture = cv2.VideoCapture(self.channel)

    # def set_average(self, num):
    #     """Set how many captures are averaged into
    #     single frame
    #     """
    #     self.average = num

    # start_acquire = pyqtSignal()
    # data_ready = pyqtSignal(np.ndarray, int)

    # @pyqtSlot()
    # def acquire(self):
    #     """Acquire 3D matrix of the data to be averaged
    #     into the single frame. In addition counts how
    #     many times no data were retrieved from the camera.
    #     """
    #     self.frame = np.zeros((self.average, self.res[1], self.res[0]),
    #                           dtype=np.dtype(np.int16))
    #     no_data_count = 0
    #     for i in range(self.average):
    #         ret, frame = self.capture.read()
    #         if not ret:
    #             no_data_count += 1
    #             continue
    #             # raise RuntimeWarning
    #         # convert to monochrome and save to self.frame
    #         if self.col_ch == 3:
    #             self.frame[i, :] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #         else:
    #             # retrieving only one channel
    #             self.frame[i, :] = frame[:, :, self.col_ch]
    #     self.construct_data()
    #     self.data_ready.emit(self.data_avg, no_data_count)
    #     return

    # def construct_data(self):
    #     """
    #     sum or mean over the averaged frames, depending if the
    #     shots are getting accumulated or averaged, respectively.
    #     """
    #     if self.accum:
    #         self.data_avg = np.rot90(np.sum(self.frame, axis=0))
    #     else:
    #         self.data_avg = np.rot90(np.mean(self.frame, axis=0))
    # _exit = pyqtSignal()

    # @pyqtSlot()
    # def exit(self):
    #     """ Try to release the capture port of
    #     the camera
    #     """
    #     try:
    #         self.capture.release()
    #         time.sleep(0.5)
    #     except Exception as e:
    #         print(f'Camera closing problem: {e}')
    #         return e


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
        self.thread.started.connect(self.radon.get_sinogram)
        self.radon.finished.connect(self.sino)
        self.radon.finished.connect(self.thread.quit)
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
        of the phantom by 360 divided by size of the sinogram"""
        self.frame = np.zeros((self.average, self.size, self.size),
                              dtype=np.dtype(np.int16))
        # for the case of aquiring more frames than sinogram size
        idx_modulo = self.idx % self.size
        # if hasattr(self, 'sinogram'):
        try:
            self.sinogram[:, :, self.average-1]
        except AttributeError:
            raise AttributeError('Data not ready')

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
