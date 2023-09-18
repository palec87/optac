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
from helpers.img_processing import norm_img, img_to_int_type
from helpers.exceptions import FallingBackException

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
        """Subtract dark image from the img.
        TODO: treating if dark correction goes negative??

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
            self.bright_corr = norm_img(self.bright_corr)
        except:
            print('Probably bright is not yet dark and hot corrected, tyring that')
            self.bright_corr = self.correct_dark(self.bright)  # this could be done only once

            self.bright_corr = self.correct_hot(self.bright_corr)  # this too
            self.bright_corr = norm_img(self.bright_corr)

        return img / self.bright_corr
    

    def correct_int(self, img_stack:np.array, mode='integral', use_bright=True, rect_dim=50):
        """OPT intensity correction over the stack of projections, preferable 
        corrected for dark, bright, and hot pixels

        Args:
            img_stack (np.array): 3D array of images, third dimension is along angles
            mode (str, optional): correction mode, only available is integral. Defaults to 'integral'.
            use_bright (bool, optional): if bright field acquisition is a ref to scale images. Defaults to True.
            rect_dim (int, optional): size of rectabgles in the corners in pixels. Defaults to 50.

        Raises:
            NotImplementedError: Checking available correction modes

        Returns:
            np.array: 3D array of the same shape as the img_stack, but intensity corrected
        """
        # do I want to correct in respect to the bright field
        # basic idea is four corners, integrated
        # second idea, fit a correction plane into the four corners.
        if use_bright is True and self.bright is not None:
            # four corners of the bright
            ref = ((self.bright[:50, :50]), 
                   (self.bright[:50, -50:]),
                   (self.bright[-50:, :50]),
                   (self.bright[-50:, -50:]),
                   )
        else:
            print('Using avg of the corners in the img stack as ref')
            # assuming the stacks 3rd dimension is the right one.
            # mean over steps in the aquisition
            ref = ((np.mean(img_stack[:50, :50, :], axis=2)), 
                   (np.mean(img_stack[:50, -50:, :], axis=2)),
                   (np.mean(img_stack[-50:, :50], axis=2)),
                   (np.mean(img_stack[-50:, -50:], axis=2)),
                   )
            
        print('shape ref[0]:', ref[0].shape)
            
        # integral takes sum over pixels of interest
        if mode=='integral':
            # sum of all pixels over all four squares
            # this is one number
            self.ref = np.mean([np.mean(k) for k in ref])
        else:
            raise NotImplementedError

        # correct the stack
        corr_stack = np.empty(img_stack.shape)

        # intensity numbers for img in the stack (sum over regions of interests)
        stack_int = []
        for i in range(img_stack.shape[2]):
            # two means are not a clean solution
            # as long as the rectangles ar the same, it is equivalent
            img_int = np.mean((np.mean(img_stack[:50, :50, i]),
                              np.mean(img_stack[:50, -50:, i]),
                              np.mean(img_stack[-50:, :50, i]),
                              np.mean(img_stack[-50:, -50:, i]),
            ))
            stack_int.append(img_int)
            corr_stack[:, :, i] = (img_stack[:, :, i] / img_int) * self.ref

        # stored in order to tract the stability fluctuations.
        self.stack_int = np.array(stack_int)
        return corr_stack


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
        self.bright_corr = norm_img(self.bright_corr)

        # step 3
        self.img_corr = self.correct_bright(self.img_corr)

        # step 4
        self.img_corr = self.correct_hot(self.img_corr)

        # step 5, make sure it is the same integer type as original img.
        self.img_corr = img_to_int_type(self.img_corr, img_format)
        
        return self.img_corr