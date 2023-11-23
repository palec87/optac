#!/usr/bin/env python


'''Widget to make a roi and bin data'''


import numpy as np
from napari.layers import Image, Shapes, Points
from magicgui import magicgui
from napari import Viewer
import napari
from typing import Annotated
import sys, os
import tqdm
sys.path.insert(1, os.path.abspath(
    'C:\\Users\\David Palecek\\Documents\\Python_projects\\optac\\optac\\src\\optac\\',),
    )

from widgets.widget_funcs import (
    select_roi,
    bin_stack_faster
)

from helpers.img_processing import (
    norm_img, img_to_int_type, is_positive,
)

from helpers.corrections import Correct


## magic gui for roi and binning
@magicgui(call_button="Select ROI")
def select_ROIs(viewer: Viewer,
                image: Image,
                points_layer: Points,
                roi_height: Annotated[int, {'max': 3000}] = 50,
                roi_width: Annotated[int, {'max': 3000}] = 50,
                bin_factor: int = 2,
              ):
    original_stack = np.asarray(image.data)
    points = np.asarray(points_layer.data)
    print(points[0])

    selected_roi = select_roi(original_stack,
                              points[0],
                              roi_height,
                              roi_width)
    
    binned_roi = bin_stack_faster(selected_roi, bin_factor)

    print(selected_roi.shape, binned_roi.shape)
    viewer.add_image(binned_roi)


# magic gui for dark-field correction
@magicgui(call_button="Correct dark/bright")
def correct_dark_bright(viewer: Viewer,
                 image: Image,
                 dark: Image,
                 bright: Image,
                 ):
    original_stack = np.asarray(image.data)

    # first correct bright field for dark
    bright_corr = bright.data - dark.data

    ans = np.empty(original_stack.shape)
    for i, img in enumerate(original_stack):
        ans[i] = img - dark.data - bright_corr

    print(ans.shape)
    viewer.add_image(ans)


# correct hot
@magicgui(call_button="Correct Hot")
def correct_hot(viewer: Viewer,
                   image: Image,
                   hot: Image,
                   std_mult: int = 7,
                 ):
    original_stack = np.asarray(image.data)
    corr = Correct(hot=hot.data, std_mult=std_mult)

    ans = np.empty(original_stack.shape)

    if ans.sndim == 3:
        for i, img in enumerate(original_stack):
            ans[i] = corr.correct_hot(img)
    else:
        ans = corr.correct_hot(img)

    print(ans.shape)
    viewer.add_image(ans)


viewer = napari.Viewer()
viewer.window.add_dock_widget(
        select_ROIs,
        name = 'Select ROI',
        )
viewer.window.add_dock_widget(
        correct_dark_bright,
        name = 'Correct Dark/Bright',
)
viewer.window.add_dock_widget(
        correct_hot,
        name = 'Correct Hot',
)

napari.run()


