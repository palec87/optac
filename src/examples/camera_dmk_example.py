from optac.src.control.camera_class import DMK
import matplotlib.pyplot as plt
# from optac.modules.dll import tisgrabber as tis
import numpy as np


def enumCodecCallback(codecname, userdata):
    """
    Callback for enumerating codecs
    :param codecname: Name of codec as byte array
    :param userdata: Python object, e.g a list for receiving the codec names
    :return: 0 for continuing, 1 for stopping the enumeration.
    """
    userdata.append(codecname.decode("utf-8"))
    return 0


cam = DMK('DMK 37BUX252')
# ret = cam.set_vid_format2(0)
ret = cam.set_vid_format("Y800 (640x480)")
# print('setting the Y16 video format', ret)
# hGrabber = cam.ic.IC_ShowDeviceSelectionDialog(None)
# prop = cam.ic.IC_printItemandElementNames(cam.g)
# print(prop)

# ret = cam.ic.IC_SetVideoFormat(cam.g, 'Mono8')
print(ret)

# cam.ic.IC_GetAvailableVideoFormats()

img = None
if cam.camera_ready():
    for i in range(3):
        cam.acquire()
        print(cam.data_avg.shape, np.amax(cam.data_avg), np.amin(cam.data_avg))
        if img is None:
            plt.imshow(cam.data_avg)
        else:
            img.set_data(cam.data_avg)
        plt.title(i)
        plt.pause(0.3)
        plt.draw()

else:
    print('Camera not there', cam.camera_ready())



print('camera ready? Answer: ', cam.camera_ready())




enumCodecCallbackfunc = cam.ic.ENUMCODECCB(enumCodecCallback)

# cam.ic.IC_InitLibrary(0)
codecs = []

cam.ic.IC_enumCodecs(enumCodecCallbackfunc, codecs)
print("Available Codecs:")
for codec in codecs:
    print(codec)

cam.release_camera()
print('camera ready? Answer: ', cam.camera_ready())
