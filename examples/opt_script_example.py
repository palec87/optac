#!/usr/bin/env python
"""
Test script of the OPTac module and OPT acquisition via script

Another example is ipynb notebook to write notebook for acquisition.
"""

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'

from optac.opt_class import Opt
# from optac.camera_class import Camera, Phonefix

exp = Opt()
print(exp.n_sweeps, exp.radon_idx)

#  need to fix channel for the cameras, mono has to be 0, and rgb 1, 2, 3
exp.init_camera('sky', port=0, channel=3, res=(640, 480))
exp.get_camera_params()

# For the case of 
# exp.camera.rotate = True
exp.get_frames(10, avg=10)
