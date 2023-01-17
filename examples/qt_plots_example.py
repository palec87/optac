'''
author: DP
Sandbox for testing pyqtgraph widgets, which are very confusing to me.
'''

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsView)
import pyqtgraph as pg
import numpy as np
import os
import sys


# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        data = np.loadtxt(os.getcwd()+'\\data\\sinogram.txt')
        self.setWindowTitle("My App")

        self.widget = QGraphicsView()
        self.imv = pg.ImageView(self.widget)
        self.imv.setImage(data, pos=(100, 100))
        self.imv.setHistogramLabel('pixel intensity')

        self.setCentralWidget(self.widget)


def main():
    # Create a Qt widget, which will be our window.
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == '__main__':
    main()
