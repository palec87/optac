#!/usr/bin/env python
"""
Threads to parallelize task withing the GUI
"""

import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal
from skimage.transform import radon
from phantoms_argonne import shepp3d

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


class Get_radon(QObject):
    def __init__(self, size):
        super(QObject, self).__init__()
        self.size = size

    finished = pyqtSignal(np.ndarray)
    progress = pyqtSignal(int)

    def get_sinogram(self):
        data = shepp3d(self.size)  # shepp-logan 3D phantom
        sinogram = np.zeros(data.shape)  # preallocate sinogram array
        angles = np.linspace(0, 360, self.size, endpoint=False)  # angles
        # TODO make progress bar with loading data
        for i in range(self.size):
            self.progress.emit(int(i*100 / self.size))
            sinogram[i, :, :] = radon(data[i, :, :], theta=angles)
        mx = np.amax(sinogram)
        sinogram = (sinogram/mx*255).astype('int16')
        self.finished.emit(sinogram)

    def loading_message(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Generating data for you")
        # msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        print(retval)
        return retval


