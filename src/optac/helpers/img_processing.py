#!/usr/bin/env python

'''
Functions related to image-processing
1. norm_img: normalization to 1 only, by max
2. img_to_int_type: casting 2d array on the specific dtype
'''

import numpy as np
import warnings

def norm_img(img: np.array, ret_type='float') -> np.array:
    """
    Normalize np.array image to 1.

    Args:
        img (np.array): img to normalize
        ret_type (str, optional): result can be casted to any valid dtype. Defaults to 'float'.

    Returns:
        np.array: normalized array to 1
    """
    return img/np.amax(img) if ret_type == 'float' else (img/np.amax(img)).astype(ret_type)


def img_to_int_type(img:np.array, dtype:np.dtype=np.int_) -> np.array:
        """After corrections, resulting array can be dtype float. Two steps are
        taken here. First convert to a chosed dtype and then clip values as if it
        was unsigned int, which the images are.shape

        Args:
            img (np.array): img to convert
            dtype (np.dtype): either np.int8 or np.int16 currently, Defaults to np.int_

        Returns:
            np.array: array as int
        """
        # ans = img.astype(dtype)
        if dtype == np.int8:
            ans = np.clip(img, 0, 255).astype(dtype)
        elif dtype == np.int16:
            ans = np.clip(img, 0, 2**16 - 1).astype(dtype)  # 4095 would be better for 12bit camera
        else:
            ans = np.clip(img, 0, np.amax(img)).astype(np.int_)
        
        return ans


def is_positive(img):
     if np.any(img < 0):
            warnings.warn('Dark-field correction: Some pixel are negative, casting them to 0.')