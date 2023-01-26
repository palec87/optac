import ctypes 
import optac.modules.dll.tisgrabber as tis
import cv2
import numpy as np

import matplotlib.pyplot as plt

from PIL import Image


ic = ctypes.cdll.LoadLibrary("./modules/dll/tisgrabber_x64.dll")
# ic = ctypes.cdll.LoadLibrary("./tisgrabber_x64.dll")

tis.declareFunctions(ic)

ic.IC_InitLibrary(0)

# hGrabber = tis.openDevice(ic)
hGrabber = ic.IC_ShowDeviceSelectionDialog(None)

# print('before setting format', ic.IC_GetFormat(hGrabber))
# print('before setting format', ic.IC_GetVideoFormat(hGrabber))

if (ic.IC_IsDevValid(hGrabber)):
    # Set the pixel format, which is to be received in the sink (memory).
    # ic.IC_SetFormat(hGrabber, tis.SinkFormats.Y16)
    ic.IC_SetFormat(hGrabber, ctypes.c_uint(4))
    # print('after setting format', ic.IC_GetFormat(hGrabber))
    # print('after setting format', ic.IC_GetVideoFormat(hGrabber))
    ic.IC_StartLive(hGrabber, 1)
    key = ""
    while key != "q":
        print("p: Process an image")
        print("q: End program")
        key = input('Enter your choice:')
        if key == "p":
            if ic.IC_SnapImage(hGrabber, int(2000)) == tis.IC_SUCCESS:
                # Declare variables of image description
                Width = ctypes.c_long()
                Height = ctypes.c_long()
                BitsPerPixel = ctypes.c_int()
                colorformat = ctypes.c_int()

                # Query the values of image description
                ic.IC_GetImageDescription(hGrabber, Width, Height,
                                          BitsPerPixel, colorformat)
                print(colorformat)

                # Calculate the buffer size, get the number of bytes per pixel
                # and the data type in the numpy array.
                elementsperpixel = 1
                dtype = np.uint8
                if colorformat.value == 0:  # tis.SinkFormats.Y800:
                    print('Y800')
                    elementsperpixel = 1  # 1 byte per pixel
                if colorformat.value == 4:  # tis.SinkFormats.Y16:
                    print('Y16')
                    dtype = np.uint16
                    elementsperpixel = 1  # 1 uint16 per pixel
                if colorformat.value == 1:  # tis.SinkFormats.RGB24:
                    print('BGR')
                    elementsperpixel = 3  # BGR format, 3 bytes
                if colorformat.value == 2:  # tis.SinkFormats.RGB32:
                    print('BGR32')
                    elementsperpixel = 4  # BGRA format, 4 bytes

                buffer_size = Width.value * Height.value * int(float(BitsPerPixel.value) / 8.0)

                # Get the image data
                imagePtr = ic.IC_GetImagePtr(hGrabber)

                imagedata = ctypes.cast(imagePtr,
                                        ctypes.POINTER(ctypes.c_ubyte *
                                                       buffer_size))

                # Create the numpy array
                image = np.ndarray(buffer=imagedata.contents,
                                   dtype=dtype,
                                   shape=(Height.value,
                                          Width.value,
                                          elementsperpixel))

                # Apply some OpenCV functions on the image
                # image = cv2.flip(image, 0)
                # image = cv2.erode(image, np.ones((11, 11)))

                plt.imshow(image)
                plt.colorbar()
                plt.show()

                cv2.imwrite('test_01.jpg', image)


            else:
                print("No frame received in 2 seconds.")

    ic.IC_StopLive(hGrabber)

    cv2.destroyWindow('Window')

else:
    ic.IC_MsgBox(tis.T("No device opened"), tis.T("Simple Live Video"))

ic.IC_ReleaseGrabber(hGrabber)
