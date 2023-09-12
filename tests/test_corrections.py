#!/usr/bin/env python

'''Test for the data correction functionalities
    - TODO: camera Hot pixel correction
    - TODO: camera dark-field correction
    - TODO: camera light-field correction
    - TODO: camera OPT LED intensity correction
'''

import pytest
import numpy as np

from optac.helpers.corrections import Correct

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


@pytest.mark.parametrize(
    'dark_img, measured_img, expected',
    [(np.ones(20).reshape(4,-1), 
      np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2]]),
      np.array([[0, 1, 0, 1, 0],
                [1, 0, 1, 0, 1],
                [0, 1, 0, 1, 0],
                [1, 0, 1, 0, 1]]),
    ),
     ])
def test_dark_corr(dark_img, measured_img, expected):
    corr = Correct(dark=dark_img)
    dcorr = corr.correct_dark(measured_img)
    assert dcorr.all() == expected.all()


@pytest.mark.parametrize(
    'hot_img, measured_img, std_mult, expected',
    [(np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 20, 2, 1],
                [2, 1, 2, 1, 2]]),
      np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 10, 2, 1],
                [2, 1, 2, 1, 2]]),
      3,
      np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 2, 2, 1],
                [2, 1, 2, 1, 2]]),
    ),
    (np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 20, 2, 1],
                [2, 1, 2, 1, 2]]),
      np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 10, 2, 1],
                [2, 1, 2, 1, 2]]),
      5,
      np.array([[1, 2, 1, 2, 1],
                [2, 1, 2, 1, 2],
                [1, 2, 10, 2, 1],
                [2, 1, 2, 1, 2]]),
    ),
     ])
def test_hot_corr(hot_img, measured_img, std_mult, expected):
    corr = Correct(hot=hot_img, std_mult=std_mult)
    print('Hot pixels', corr.hot_pxs)
    dcorr = corr.correct_hot(measured_img)

    print(dcorr)
    assert dcorr.all() == expected.all()