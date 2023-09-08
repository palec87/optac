#!/usr/bin/env python

'''Test for the data correction functionalities
    - TODO: camera Hot pixel correction
    - TODO: camera dark-field correction
    - TODO: camera light-field correction
    - TODO: camera OPT LED intensity correction
'''

import pytest
import numpy as np

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'

@pytest.mark.parametrize(
    'hot_px_lst, measured, expected',
    [([(0, 0), (1, 3), (3, 1)], np.linspace(20).reshape(4,-1), ),
     ])
def test_hot_px_corr(hot_px_lst, measured, expected):
    pass