#!/usr/bin/env python
"""
Threads to parallelize task withing the GUI
"""

import numpy as np
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
        for i in range(self.size):
            self.progress.emit(int(i*100 / self.size))
            sinogram[i, :, :] = radon(data[i, :, :], theta=angles)
        self.finished.emit(sinogram)
