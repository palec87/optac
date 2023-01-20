import ctypes
import optac.modules.dll.tisgrabber as tis
import os

print(os.getcwd())

ic = ctypes.cdll.LoadLibrary("./modules/dll/tisgrabber_x64.dll")
tis.declareFunctions(ic)
ic.IC_InitLibrary(0)
# hGrabber = tis.openDevice(ic)

camera = ic.IC_ShowDeviceSelectionDialog(None)
# ic.IC_SetContinuousMode(camera, 0)
# ic.IC_StartLive(camera, 1)
ret = ic.IC_SetFormat(camera, int(1))
print(ret, tis.IC_SUCCESS)
format = ic.IC_GetFormat(camera)
print(format)

if (ic.IC_IsDevValid(camera)):
    ic.IC_StartLive(camera, 1)
    key = ""
    while key != "q":
        print("s: Save an image")
        print("q: End program")
        key = input('Enter your choice:')
        if key == "s":
            if ic.IC_SnapImage(camera, int(2000)) == tis.IC_SUCCESS:
                ic.IC_SaveImage(camera, tis.T("test.bmp"),
                                tis.ImageFileTypes['BMP'], int(100))
                print("Image saved.")
            else:
                print("No frame received in 2 seconds.")

    ic.IC_StopLive(camera)
else:
    ic.IC_MsgBox(tis.T("No device opened"), tis.T("Simple Live Video"))

ic.IC_ReleaseGrabber(camera)
