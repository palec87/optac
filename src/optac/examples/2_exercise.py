import numpy as np
from napari.layers import Image, Labels
from magicgui import magicgui
import napari

from skimage import data
from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.morphology import closing, square, remove_small_objects
from skimage.color import label2rgb

@magicgui(call_button="Apply threshold")
def segment(image_layer :Image, 
            thresh: int = 120,
            size: int = 4,
            obj_min_size: int = 20) -> Labels:
    
    data = image_layer.data
    bw = closing(data > thresh, square(size))
    cleared = remove_small_objects(clear_border(bw), obj_min_size)
    label_image = label(cleared)
    # try:
    #     viewer.layers['segment_label'].data = label_image
    # except:
    #     label_image = viewer.add_labels(label_image, name='segment_label')
    return Labels(label_image)

viewer = napari.Viewer()

viewer.window.add_dock_widget(segment,
                              name = 'Threshold widged')
napari.run()