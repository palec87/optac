#!/usr/bin/env python

'''Corrections module'''

import numpy as np


class HotPx(object):
    def __init__(self, hot_img, std_mult):
        self.hot_img = hot_img
        self.std_mult = std_mult
        self.hot_img_shape = self.hot_img.shape

        self.get_hot_pxs()

    def get_hot_pxs(self):
        self.mean = np.mean(self.hot_img, dtype=np.float64)
        self.std = np.std(self.hot_img, dtype=np.float64)

        self.mask = np.ma.masked_greater(
                                self.hot_img, 
                                self.mean + self.std_mult * self.std,
                                )
        hot_pxs = []
        for j, k in zip(*np.where(self.mask.mask)):
            hot_pxs.append((j, k))
        self.hot_pxs = hot_pxs
    
    def correct_hot(self, img, mode='n4'):
        # check if the shapes of the correction and image match
        if self.hot_img_shape != img.shape:
            raise IndexError('images do not have the same shape')
        
        # defining neighbours
        if mode=='n4':
            neighs = [(-1, 0), (0, -1), (0, 1), (1, 0)] # U, L, R, D
        elif mode=='n8':
            neighs = [(-1, -1), (-1, 0), (-1, 1),
                     (0, -1), (0, 1),
                     (1, -1), (1, 0), (1, 1),
                     ]
        else:
            raise ValueError('Unknown mode option, valid is n4 and n8.')

        self.corrected = img.copy()

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

            self.corrected[hot_px] = int(np.mean(neigh_vals))


class DarkField(object):
    def __init__(self, dark, hot_img):
        self.dark = dark
        self.hot_img = hot_img
        self.dark_shape = self.dark.shape

    def correct_dark(self, img, correct_hot=False):
        if self.dark_shape != img.shape:
            raise IndexError('images do not have the same shape')
        
        if correct_hot:
            raise NotImplementedError
        
        self.corrected = img - self.dark