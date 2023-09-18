#!/usr/bin/env python


'''
Functions useful for simulation of artificial data and checking concepts
'''


import numpy as np


def _gen_img_stack_noise(img: np.array, stack_size=64, std=0.2) -> np.array:
    # generate stack of data where image is multiplied by factor from normal
    #  ditribution
    # N(mu=mean(pixels), sigma=std(in percents of mu))
    # means that all pixels oscillate the same

    # preallocate
    out = np.empty((img.shape[0], img.shape[1], stack_size))

    # mean of the input image
    # mean_img = np.mean(img)

    # 1d array of the multiplier (samples from normal distro)
    mult_factors = np.random.normal(1, std, stack_size)
    for i in range(stack_size):
        # multiply amd put to the array 
        out[:, :, i] = img * mult_factors[i]

    return out


def _add_noise_arr(arr, noise_level=0.05):
    # add noise level which is percentage of the mean of the array

    mean = np.mean(arr)

    # generate noise and reshape
    noise = np.random.normal(loc=0,
                             scale=mean*noise_level,
                             size=np.prod(arr.shape)).reshape(arr.shape)
    # add noise
    return arr + noise



