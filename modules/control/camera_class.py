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

import os
import numpy as np
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
import cv2
from modules.control.threading_class import Get_radon
import time
from ctypes import (
    cdll, Structure, c_float, c_int, c_long, c_ubyte, c_uint,
    cast, POINTER
)

import xml.etree.ElementTree as ET

import optac.modules.dll.tisgrabber as tis


__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


class CallbackUserdata(Structure):
    """ Example for user data passed to the callback function. """
    def __init__(self):
        self.width = 0
        self.height = 0
        self.BytesPerPixel = 0
        self.buffer_size = 0
        self.oldbrightness = 0
        self.getNextImage = 0
        self.cvMat = None


class DMK(QObject):
    def __init__(self, name) -> None:
        super().__init__()
        self.ic = cdll.LoadLibrary("./modules/dll/tisgrabber_x64.dll")
        tis.declareFunctions(self.ic)
        self.ic.IC_InitLibrary(0)
        self.name = name
        self.camera = None
        self.saving = False
        self.accum = False
        self.rotate = False

        self.format = None
        self.binning = 0
        self.skipping = 0

        self.counter = 0
        # self.exit()
        self.select_camera()

    def select_camera(self):
        # self.create_grabber()
        self.camera = self.ic.IC_ShowDeviceSelectionDialog(None)
        print('saving xml')
        self.ic.IC_SaveDeviceStateToFile(self.camera, tis.T("device.xml"))

        print('reading xml back to retrieve settings')
        self.parse_camera_state_xml()

        self.ic.IC_SetFormat(self.camera, c_uint(self.format))

        self.Callbackfunc = self.ic.FRAMEREADYCALLBACK(self.img_callback)
        self.data = CallbackUserdata()
        self.ic.IC_SetFrameReadyCallback(
            self.camera,
            self.Callbackfunc,
            self.data,
            )

        # this does not work, return always 6
        self.format_string = self.ic.IC_GetVideoFormat(self.camera)
        print('current format string: ', self.format_string)

    def parse_camera_state_xml(self):
        mytree = ET.parse('device.xml')
        myroot = mytree.getroot()
        for x in myroot.findall('device/videoformat'):
            print(x.text, type(x.text))

        format = x.text.split()[0]
        if format == 'Y16':
            self.format = 4
        elif format == 'Y800':
            self.format = 0
        else:
            raise ValueError('You have to select either Y16 or Y800,\
                Initialize the camera again.')

    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, int)

    @pyqtSlot()
    def acquire(self):
        for i in range(self.average):
            self.data.getNextImage = 1
            while self.data.getNextImage != 0:
                time.sleep(0.001)
            self.get_img_from_data()

            if i == 0:
                self.frame = self.current_img
            elif i == 1:
                self.frame = np.concatenate(
                    (self.frame[np.newaxis, :], 
                     self.current_img[np.newaxis, :],
                    )
                )
            else:
                self.frame = np.concatenate(
                    (self.frame,
                     self.current_img[np.newaxis, :],
                     ),
                )
        self.construct_data()
        self.data_ready.emit(self.data_avg, 0)

    def img_callback(self, hGrabber, buffer, framenumber, data):
        """ This is an example callback function for image processing  with
            OpenCV
        :param: hGrabber: This is the real pointer to the grabber object.
        :param: pBuffer : Pointer to the first pixel's first byte
        :param: framenumber : Number of the frame since the stream started
        :param: pData : Pointer to additional user data structure
        """
        if data.getNextImage == 1:
            data.getNextImage = 2
            if data.buffer_size > 0:
                image = cast(buffer, POINTER(c_ubyte * data.buffer_size))
                data.cvMat = np.ndarray(buffer=image.contents,
                                        dtype=data.dtype,
                                        shape=(data.height.value,
                                               data.width.value,
                                               data.elements_per_pixel))
            data.getNextImage = 0
            # return data.cvMat

    def startCamera(self, wid):
        '''Start the passed camera
        :param UserData user data connected with the camera
        :param Camera The camera to start
        '''
        self.ic.IC_SetContinuousMode(self.camera, 0)
        self.ic.IC_SetHWnd(self.camera, int(wid))
        self.ic.IC_StartLive(self.camera, 1)
        self.CreateUserData(self.data, self.camera)

    def CreateUserData(self, ud, camera):
        ''' Create the user data for callback for the passed camera
        :param ud User data to create
        :param camera The camera connected to the user data
        '''
        ud.width = c_long()
        ud.height = c_long()
        bits_per_pixel = c_int()
        color_format = c_int()

        # Query the values
        self.ic.IC_GetImageDescription(camera, ud.width, ud.height,
                                       bits_per_pixel, color_format)

        ud.dtype, ud.elements_per_pixel = self._elements_per_pixel(color_format)

        # print('bits per pixel: ', bits_per_pixel.value)
        # print('color format: ', color_format, ud.elements_per_pixel)
        ud.buffer_size = ud.height.value * ud.width.value * int(float(bits_per_pixel.value) / 8.0)
        ud.getNextImage = 0

    def _elements_per_pixel(self, color_format):
        # Calculate the buffer size, get the number of bytes per pixel
        # and the data type in the numpy array.
        # tis.SinkFormats.Y800 and others do not work for me
        elements_per_pixel = 1
        dtype = np.uint8
        if color_format.value == 0:  # tis.SinkFormats.Y800:
            elements_per_pixel = 1  # 1 byte per pixel
        if color_format.value == 4:  # tis.SinkFormats.Y16:
            dtype = np.uint16
            elements_per_pixel = 1  # 1 uint16 per pixel
        # In other part I throw error if RGB, but future cameras can be RGB
        if color_format.value == 1:  # tis.SinkFormats.RGB24:
            elements_per_pixel = 3  # BGR format, 3 bytes
        if color_format.value == 2:  # tis.SinkFormats.RGB32:
            elements_per_pixel = 4  # BGRA format, 4 bytes
        return dtype, elements_per_pixel

    def snap_image(self):
        self.data.getNextImage = 1
        while self.data.getNextImage != 0:
            time.sleep(0.005)
        self.get_img_from_data()
        print("snapping done")

    def get_img_from_data(self):
        # here has to be devision between 8bit and 16bit
        if self.format == 4:  # Y16
            self.current_img = cv2.flip(self.data.cvMat >> 4, 0)
        elif self.format == 0:  # Y800
            self.current_img = cv2.flip(self.data.cvMat, 0)
        else:
            raise ValueError('Wrong image format.')
    
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

    # def save_current_img(self):
    #     # Here we (should) have our image in data as numpy // cv Matrix
    #     name = 'data_' + str(self.counter) + '.tiff'
    #     cv2.imwrite(name, self.current_img)
    #     self.counter += 1

    # def create_grabber(self):
    #     try:
    #         self.g = self.ic.IC_CreateGrabber()
    #         self.ic.IC_OpenVideoCaptureDevice(
    #             self.g,
    #             tis.T(self.name),
    #             )
    #     except AttributeError as e:
    #         print(f'Wrong name, {e}')
    #     else:
    #         print('Video grabber created')

    # def set_vid_format(self, value: str) -> None:
    #     """Can be only set when not streaming
    #     TODO: check for that

    #     Args:
    #         value (str): one of the Y800, Y16, RGB24,\
    #             RGB32, YUY2, Y411
    #     """
    #     self.vid_format = value
    #     ret = self.ic.IC_SetVideoFormat(
    #         self.g,
    #         tis.T(value),
    #         )
    #     return ret

    # def set_vid_format2(self, value: int) -> None:
    #     """Can be only set when not streaming
    #     TODO: check for that

    #     Args:
    #         value (int):    Y800 = 0
    #                         RGB24 = 1
    #                         RGB32 = 2
    #                         UYVY = 3
    #                         Y16 = 4
    #     """
    #     self.vid_format = value
    #     ret = self.ic.IC_SetVideoFormat(
    #         self.g,
    #         c_int(value),
    #         )
    #     return ret

    def set_frame_rate(self, value: float) -> None:
        self.frame_rate = value
        self.ic.IC_SetFrameRate(self.g, c_float(value))

    def set_binning(self, value: int):
        self.binning = value
        if self.binning > 0:
            self.ic.IC_SetVideoFormat(
                self.g,
                tis.T(
                    ' '.join(
                        self.vid_format,
                        '[Binning',
                        str(self.binning)+'x]')
                    ),
                )

    def set_skipping(self, value: int):
        self.skipping = value
        if self.skipping > 0:
            self.ic.IC_SetVideoFormat(
                self.g,
                tis.T(
                    ' '.join(
                            self.vid_format,
                            '[Skipping',
                            str(self.skipping)+'x]')
                    ),
                )

    def set_exposure(self, value: float) -> None:
        ret = self.ic.IC_SetPropertyAbsoluteValue(
                self.g,
                "Exposure".encode("utf-8"),
                "Value".encode("utf-8"), c_float(value))

        # self._handle_ret_from_set_property()
        self.exposure = value

    def set_gain(self, value):
        ret = self.ic.IC_SetPropertyAbsoluteValue(
                self.g,
                "Gain".encode("utf-8"),
                "Value".encode("utf-8"), c_float(value))
        # self._handle_ret_from_set_property()
        self.gain = value

    def set_average(self, num):
        """
        How many captures are averaged into a single frame.

        Args:
            num (int): Number of averages
        """
        self.average = num

    def camera_ready(self):
        return self.ic.IC_IsDevValid(self.camera)

    _exit = pyqtSignal()

    @pyqtSlot()
    def exit(self):
        """
        Release the capture port of the camera,
        otherwise raise an exception
        """
        if self.camera is None:
            return
        if self.ic.IC_IsDevValid(self.camera):
            print('stopping live')
            self.ic.IC_StopLive(self.camera)

        try:
            self.ic.IC_ReleaseGrabber(self.camera)
            print('release grabber')
            time.sleep(0.5)
        except Exception as e:
            print(f'Camera closing problem: {e}')
            return e

    # def exit(self):  # originally close()
        

    # start_acquire = pyqtSignal()
    # data_ready = pyqtSignal(np.ndarray, int)

    # @pyqtSlot()
    # def acquire(self):
    #     no_data_count = []
    #     self.ic.IC_SetVideoFormat(self.camera, tis.T("Y16 (1280x720)"))
    #     self.ic.IC_StartLive(self.camera, 0)
    #     if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
    #         # Declare variables of image description
    #         Width = c_long()
    #         Height = c_long()
    #         BitsPerPixel = c_int()
    #         colorformat = c_int()

    #         # Query the values of image description
    #         self.ic.IC_GetImageDescription(
    #             self.camera, Width, Height,
    #             BitsPerPixel, colorformat)

    #         # Calculate the buffer size
    #         bpp = int(BitsPerPixel.value / 8.0)
    #         print('bpp', BitsPerPixel.value, colorformat)
    #         buffer_size = Width.value * Height.value * BitsPerPixel.value

    #         # Get the image data
    #         imagePtr = self.ic.IC_GetImagePtr(self.camera)

    #         imagedata = cast(imagePtr,
    #                          POINTER(c_ubyte *
    #                                  buffer_size))

    #         # Create the numpy array
    #         self.data_avg = np.ndarray(
    #                     buffer=imagedata.contents,
    #                     dtype=np.uint8,
    #                     shape=(Height.value,
    #                            Width.value,
    #                            bpp))
    #         no_data_count.append(0)
    #     else:
    #         no_data_count.append(1)
    #         print("No frame received in 2 seconds.")
    #     self.data_ready.emit(self.data_avg, no_data_count)
    #     self.ic.IC_StopLive(self.camera)


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
