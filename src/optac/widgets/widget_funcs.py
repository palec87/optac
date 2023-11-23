#!/usr/bin/env python

import numpy as np
from tqdm import tqdm


def select_roi(stack, ur_corner, height, width):
    _, ix, iy = ur_corner.astype(int)
    roi = stack[:,
                ix: ix + height,
                iy: iy + width]
    return roi

def bin_stack(stack, bin_factor):
    if len(stack.shape) != 3:
        raise IndexError('Stack has to have three dimensions.')
    
    height_dim = stack.shape[1] // bin_factor
    width_dim = stack.shape[2] // bin_factor
    ans = np.empty((stack.shape[0],
                    height_dim,
                    width_dim),
                   dtype=int)
    for i in tqdm(range(stack.shape[0])):
        for j in range(height_dim):
            for k in range(width_dim):
                ans[i, j, k] = np.sum(
                                  stack[i,
                                        j*bin_factor: (j+1)*bin_factor,
                                        k*bin_factor: (k+1)*bin_factor],
                                      )
    return ans


def bin_stack_faster(stack, bin_factor):
    if len(stack.shape) != 3:
        raise IndexError('Stack has to have three dimensions.')
    
    height_dim = stack.shape[1] // bin_factor
    width_dim = stack.shape[2] // bin_factor
    ans = np.empty((stack.shape[0],
                    height_dim,
                    width_dim),
                   dtype=int)
    for i in tqdm(range(stack.shape[0])):
        ans[i] = stack[i].reshape(height_dim, bin_factor,
                                  width_dim, bin_factor).sum(3).sum(1)
    return ans