import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
import cv2
from phantoms_argonne import shepp3d
from skimage.transform import radon
from threading_class import Get_radon
import time


# TODO need to implement camera shutdown
# TODO if it can do hardware binning, implement it, otherwise only software one
# TODO no software binning yet
class Sky_basic(QObject):
    def __init__(self, channel, col_ch, resolution, bin_factor) -> None:
        super(QObject, self).__init__()
        self.channel = channel  # which video input to use (typically 1 or 2)
        self.res = resolution  # tuple (1920,1080), (1280,720), (640,480)
        # self.average = average
        self.binning_factor = bin_factor  # not sure it can do hardware binning
        self.accum = False
        self.col_ch = col_ch
        self.initialize()

    def initialize(self):
        self.capture = cv2.VideoCapture(1)

    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, int, list)

    @pyqtSlot()
    def acquire(self):  # acquires full matrix
        self.frame = np.zeros((self.average, self.res[1], self.res[0]),
                              dtype=np.dtype(np.int16))
        self.minmax = []
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
            # tracking minmax (should disappear to speed up)
            self.minmax.append(0)
            #     (np.amax(self.frame[i, :]),
            #      np.amin(self.frame[i, :]))
            # )
        self.construct_data()
        self.data_ready.emit(self.data_avg, no_data_count, self.minmax)
        return

    def construct_data(self):
        if self.accum:
            self.data_avg = np.sum(self.frame, axis=0)
        else:
            self.data_avg = np.mean(self.frame, axis=0)
    _exit = pyqtSignal()

    @pyqtSlot()
    def exit(self):
        try:
            self.capture.release()
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
        self.thread.started.connect(self.radon.get_sinogram)
        self.radon.finished.connect(self.sino)
        self.radon.finished.connect(self.thread.quit)
        # self.radon.finished.connect(self.radon.deleteLater)
        self.thread.finished.connect(self.thread.quit)
        self.radon.progress.connect(self.report_progress)
        self.thread.start()

    def sino(self, data):
        print('setting sino variable')
        self.sinogram = data
        # self.thread.quit()

    def report_progress(self, n):
        print(n)

    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, int, list)

    @pyqtSlot()
    def acquire(self):
        self.frame = np.zeros((self.average, self.size, self.size),
                              dtype=np.dtype(np.int16))
        for i in range(self.average):
            self.frame[i, :] = self.sinogram[:, :, self.idx]
            time.sleep(0.01)

        self.construct_data()
        self.data_ready.emit(self.data_avg, 0, list(np.zeros(self.average)))
        # return

    def construct_data(self):
        if self.accum:
            self.data_avg = np.sum(self.frame, axis=0)
        else:
            self.data_avg = np.mean(self.frame, axis=0)

    _exit = pyqtSignal()

    @pyqtSlot()
    def exit(self):
        return
