import numpy as np
from napari.layers import Image, Labels
from magicgui import magicgui
import napari

@magicgui(call_button="Apply threshold")
def threshold_img(image_layer :Image, 
               thresold: int = 120)->Labels:
    
    data = image_layer.data
    result = data > thresold
    return Labels(result)

viewer = napari.Viewer()

viewer.window.add_dock_widget(threshold_img,
                              name = 'Threshold widged')
napari.run()