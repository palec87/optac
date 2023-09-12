#!/usr/bin/env python

'''
Corrections module for the microscopy acquisition

corrections available:

#. Dark-field correction

  * Always applicable and should be always done

#. Flat-field, ie bright-field correction

  * Applicable only transmission measurements

#. Hot pixel correction

  * Hot pixels identified from long exposure acquisition on the blocked camera

  * Possible to correct as mean of 4 or 8 neighbours
  
  * Might not be necessary for the transmission measurements

#. TODO: Intensity correction

  * More crucial for the shorter exposure times (depends on which time-scale the light-source drifts.)

Notes:

* Exposure on the dark and bright field corrections must be same and same as the experimental exposure.
* TODO: Need to ensure correct logic of the correction and their redefinition.

'''

import numpy as np

class Correct(object):
    """Correcting raw data from 2D array acquisitions. Currently implemented
    corrections are:

    #. Dark-field
    #. Bright-field
    #. Hot-pixel correction
    #. TODO: intensity correction.

    Args:
        object (object): general python object
    """
    def __init__(self, hot=None, std_mult=7, dark=None, bright=None):
        self.hot = hot
        self.std_mult = std_mult

        self.dark = dark
        self.dark_corr = None
        
        self.bright = bright
        self.bright_corr = None

        if hot is not None:
            self.get_hot_pxs()


    def get_hot_pxs(self):
        """
        Identify hot pixels from the hot array based on the hot
        std_mutl facter threshold. Hot pixel has intensity greater than

        mean(img) + std_mult * std(img)
        """
        self.mean = np.mean(self.hot, dtype=np.float64)
        self.std = np.std(self.hot, dtype=np.float64)

        self.mask = np.ma.masked_greater(
                                self.hot, 
                                self.mean + self.std_mult * self.std,
                                )
        hot_pxs = []
        for j, k in zip(*np.where(self.mask.mask)):
            hot_pxs.append((j, k))
        self.hot_pxs = hot_pxs

    def correct_hot(self, img, mode='n4'):
        """Correct hot pixels from its neighbour pixel values. It ignores the
        neighbour pixel if it was identified as hot pixel itself.

        Args:
            img (np.array): image to be corrected.
            mode (str, optional): How to pick neighbours. Defaults to 'n4', up, bottom
            left, right. Other option is n8, which takes the diagonal neighbours too.

        Raises:
            IndexError: Raised if the hot_corr array does not match the shape of the input img.
            ValueError: invalid mode option

        Returns:
            np.array: Corrected img array
        """
        # check if the shapes of the correction and image match
        if self.hot.shape != img.shape:
            raise IndexError('images do not have the same shape')
        
        # define neighbours
        if mode=='n4':
            neighs = [(-1, 0), (0, -1), (0, 1), (1, 0)] # U, L, R, D
        elif mode=='n8':
            neighs = [(-1, -1), (-1, 0), (-1, 1),
                     (0, -1), (0, 1),
                     (1, -1), (1, 0), (1, 1),
                     ]
        else:
            raise ValueError('Unknown mode option, valid is n4 and n8.')

        ans = img.copy()

        # loop over identified hot pixels and correct
        for hot_px in self.hot_pxs:
            neigh_vals = []
            for neigh in neighs:
                px = np.add(np.array(hot_px), np.array(neigh))
                # I can do this because I checked shapes above
                # check if neighbour is out of the image ranges.
                if 0 > px[0] or px[0] >= img.shape[0] or 0 > px[1] or px[1] >= img.shape[1]:
                    continue
                
                # ignore if neighbour is hot pixel
                if tuple(px) in self.hot_pxs:
                    continue
                
                neigh_vals.append(img[px[0], px[1]])

            ans[hot_px] = int(np.mean(neigh_vals))
        return ans


    def correct_dark(self, img):
        """Subtract dark image from the img

        Args:
            img (np.array): Img to be corrected

        Raises:
            IndexError: If the shapes do not match

        Returns:
            np.array: corrected image
        """
        if self.dark.shape != img.shape:
            raise IndexError('images do not have the same shape')
        
        return img - self.dark


    def correct_bright(self, img: np.array) -> np.array:
        """Correct image using a bright-field correction image

        Args:
            img (np.arrays): Img to correct

        Raises:
            IndexError: If the shapes do not match

        Returns:
            np.array: Corrected image
        """
        if self.bright.shape != img.shape:
            raise IndexError('images do not have the same shape')

        # direct correction or bright needs to be first corrected with dark and hot pixels.
        try:
            self.bright_corr = self.norm_img(self.bright_corr)
        except:
            print('Probably bright is not yet dark and hot corrected, tyring that')
            self.bright_corr = self.correct_dark(self.bright)  # this could be done only once

            self.bright_corr = self.correct_hot(self.bright_corr)  # this too
            self.bright_corr = self.norm_img(self.bright_corr)

        return img / self.bright_corr


    def norm_img(self, img: np.array, ret_type='float') -> np.array:
        """Normalize np.array image to 1.

        Args:
            img (np.array): img to normalize
            ret_type (str, optional): result can be casted to any valid dtype. Defaults to 'float'.

        Returns:
            np.array: normalized array to 1
        """
        return img/np.amax(img) if ret_type == 'float' else (img/np.amax(img)).astype(ret_type)


    def img_to_inttype(self, img:np.array, dtype:np.dtype=np.int16) -> np.array:
        """After corrections, resulting array can be dtype float. Two steps are
        taken here. First convert to a chosed dtype and then clip values as if it
        was unsigned int, which the images are.shape

        Args:
            img (np.array): img to convert
            dtype (np.dtype): either np.int8 or np.int16 currently, Defaults to np.int16

        Raises:
            NotImplementedError: dtype not implemented

        Returns:
            np.array: array as int
        """
        ans = img.astype(dtype)
        if dtype == np.int8:
            ans = np.clip(ans, 0, 255)
        elif dtype == np.int16:
            ans = np.clip(ans, 0, 2**16 - 1)  # 4095 would be better for 12bit camera
        else:
            raise NotImplementedError(f'{dtype} not implemented.')
        
        return ans


    def correct_all(self, img: np.array, mode_hot='n4') -> np.array:
        """
        Perform all available corrections for single np.array image.

        1. subtract dark from img and white
        2. remove hot pixels from white
        3. correct white in the img
        4. remove hot pixels from img

        Args:
            img (np.array): img to correct
            mode_hot (str, optional): mode of selecting hot pixel neighbours. Defaults to 'n4'.

        Returns:
            np.array: Fully corrected image, also casted to the original dtype
        """
        # TODO: this leads to repetition of steps I think
        img_format = img.dtype()

        # step 1
        self.img_corr = self.correct_dark(img)
        self.bright_corr = self.correct_dark(self.bright)  # this could be done only once

        # step 2
        self.bright_corr = self.correct_hot(self.bright_corr, mode=mode_hot)  # this too
        self.bright_corr = self.norm_img(self.bright_corr)

        # step 3
        self.img_corr = self.correct_bright(self.img_corr)

        # step 4
        self.img_corr = self.correct_hot(self.img_corr)

        # step 5, make sure it is the same integer type as original img.
        self.img_corr = self.img_to_inttype(self.img_corr, img_format)
        
        return self.img_corr