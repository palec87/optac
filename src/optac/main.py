#!/usr/bin/env python
"""
Acquisition software for Optical Projection Tomography. If you are
interested in reconstruction and analysis, see project \
`OPTan <https://github.com/palec87/optan>`_.

You can start cheap with the OPT with this GUI. 28BYJ-48 stepper motor and
Sky basics camera cost 2.44 and 40 bucks, respectively.

Control of the motors is done via Arduino board, notes on board
wiring can be found in the docs (TODO docs)

TODO ROI for the cameras which support that.
TODO Save images into a check radio button.
TODO Plotting 3d needs to be separate class or left to napari.

Small motor which comes with Arduino starting kit (28BYJ-48) is
denoted as Uno-stepper
"""

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'

import sys
import os
from time import gmtime, strftime, sleep
import cv2
import json
import numpy as np
from functools import partial

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from gui.optac_ui import Ui_MainWindow
from gui.optac_ui_outreach import Ui_MainWindow as Outreach
import pyqtgraph as pg

# this is here for pyinstaller only, so it is a workaround
from telemetrix import telemetrix

from control.motor_class import Stepper
from control.camera_class import (
    Sky_basic,
    Virtual,
    Phonefix,
    DMK)
from helpers.opt_class import Data
from helpers.radon_back_projection import Radon

from helpers.exceptions import NoMotorInitialized

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'

# config #
#########
pg.setConfigOption('background', 'd')
pg.setConfigOption('foreground', 'k')

##################
# Outline:
# 1. INIT
# 2. UI interfacing
# 3. Execute buttons
# 4. Initialize HW
# 5. Counters
# 6. Acquisition
# 7. Metadata, saving, reporting
# 8. PLOTTING
# 9. STATE methods
# 10. MESSAGES
# Main
###################


class Gui(QtWidgets.QMainWindow):
    def __init__(self, init_values_file):
        super(Gui, self).__init__()
        self.ui = Outreach()#Ui_MainWindow()
        self.ui.setupUi(self)
        self.show()
        self.create_plots()

        self.init_file = init_values_file
        self.stop_request = False
        self.idle = True
        self.simul_mode = False
        self.motor_on = False
        self.motor_wait = 0.001
        self.camera_on = False
        self.opt_running = False
        self.save_opt = True
        self.cont_opt = False
        self.stop_opt = False
        self.min_hist = None
        self.max_hist = None
        self.rotate = 'no'
        self.motor_steps = None
        self.channel = 3
        self.camera_port = None
        self.simul_angles = 128  # Number of rotation angles for Virtual camera
        self.frame_count = 0
        self.no_data_count = 0
        self.metadata = {}
        self.toggle_hist = False
        self.exp_path = None

        # add logo
        self.pixmap = QPixmap('data\\logo3.png')
        self.ui.logo.setPixmap(self.pixmap)
        self.ui.logo.resize(
            self.pixmap.width(),
            self.pixmap.height(),
        )
        # link GUI objects in optac_ui.py
        # and the methods from this class

        # motor control values
        self.ui.motor_speed.valueChanged.connect(self._update_motor_speed)
        self.ui.angle.valueChanged.connect(self._update_motor_angle)
        self.ui.motor_wait_const.valueChanged.connect(self._update_motor_wait)
        self.ui.motor_steps.valueChanged.connect(self._update_motor_steps)
        self.ui.abs_position.valueChanged.connect(self._update_abs_pos)
        # motor buttons
        self.ui.rotate_cont_btn.clicked.connect(self.exec_rotate_cont_btn)
        self.ui.stop_rotate_cont_btn.clicked.connect(
            self.exec_stop_rotate_cont_btn)
        self.ui.step_motor_btn.clicked.connect(self.exec_step_motor_btn)
        self.ui.step_abs_btn.clicked.connect(self.exec_step_abs_btn)
        self.ui.motor_init_btn.clicked.connect(self.exec_motor_init_btn)
        self.ui.motor_close_btn.clicked.connect(self.exec_motor_close_btn)
        self.ui.motor_close_btn.setDisabled(True)

        self.ui.motor_type_list.currentIndexChanged.connect(
            self._update_motor_type
            )
        self.ui.motor_type_list.addItem('Uno-stepper')
        self.ui.motor_type_list.addItem('nanotec')

        # camera settings
        self.ui.camera_type_list.currentIndexChanged.connect(
            self._update_camera_type
            )
        self.ui.camera_type_list.addItems(
            ['virtual', 'Sky (1280x720)', 'Phonefix', 'DMK'],
            )
        self.ui.camera_port.valueChanged.connect(self._update_camera_port)
        self.ui.camera_init_btn.clicked.connect(self.initialize_camera)
        self.ui.camera_prop_btn.clicked.connect(self._show_camera_settings)

        # corrections
        self.ui.flat_field_btn.clicked.connect(self.exec_flat_field)
        self.ui.dark_field_btn.clicked.connect(self.exec_dark_field)
        self.ui.hot_pixels_btn.clicked.connect(self.exec_hot_pixels)
        self.ui.hot_pixel_std_multiple.valueChanged.connect(
            self._update_hot_std_mult,
            )
        self.ui.corr_averages.valueChanged.connect(self._update_corr_averages)
        
        # snap camera
        self.ui.snap_dmk_btn.clicked.connect(self.snap_dmk)
        # horizontal cut plot
        self.ui.hline1_px.valueChanged.connect(self._update_hor_cut_pxs)
        self.ui.hline2_px.valueChanged.connect(self._update_hor_cut_pxs)
        self.ui.show_hlines.toggled.connect(self._update_show_hlines)

        # saving
        self.ui.save_image_btn.clicked.connect(self.exec_save_image_btn)

        self.ui.red_ch.toggled.connect(self._update_camera_channels)
        self.ui.green_ch.toggled.connect(self._update_camera_channels)
        self.ui.blue_ch.toggled.connect(self._update_camera_channels)
        self.ui.amp_ch.toggled.connect(self._update_camera_channels)

        # acquire settings
        self.ui.get_n_frames_btn.clicked.connect(self.exec_get_n_frames_btn)
        self.ui.n_frames.valueChanged.connect(self._update_n_frames)
        self.ui.frames2avg.valueChanged.connect(self._update_frames_to_avg)
        self.ui.accum_shots.toggled.connect(self._update_accum_shots)

        # measure panel
        self.ui.run_opt_btn.clicked.connect(self.exec_run_opt_btn)
        self.ui.start_cont_opt_btn.clicked.connect(self.exec_start_cont_opt)
        self.ui.stop_cont_opt_btn.clicked.connect(self.exec_stop_cont_opt)
        self.ui.live_recon.toggled.connect(self._update_live_recon_btn)
        self.ui.live_recon_3d.toggled.connect(self._update_live_recon_3d_btn)
        self.ui.save_opt.toggled.connect(self._update_save_opt)
        self.ui.show_3d_btn.clicked.connect(self.exec_show_3d_btn)
        self.ui.show_3d_btn2.clicked.connect(self.exec_show_3d_btn2)
        self.ui.radon_idx.valueChanged.connect(self._update_radon_idx)
        self.ui.n_sweeps.valueChanged.connect(self._update_n_sweeps)

        # recon rectangle
        self.ui.ulx.valueChanged.connect(self._update_rect)
        self.ui.uly.valueChanged.connect(self._update_rect)
        self.ui.brx.valueChanged.connect(self._update_rect)
        self.ui.bry.valueChanged.connect(self._update_rect)

        # Control panel
        self.ui.stop_btn.clicked.connect(self.exec_stop_btn)
        self.ui.exit_btn.clicked.connect(self.exec_exit_btn)
        self.ui.folder_btn.clicked.connect(self.select_folder)

        # plot control
        self.ui.toggle_hist.toggled.connect(self._update_toggle_hist)
        self.ui.min_hist.valueChanged.connect(self._update_hist_min)
        self.ui.max_hist.valueChanged.connect(self._update_hist_max)

        self.ui.no_rotate.toggled.connect(self._update_rotate_frame)
        self.ui.rotate_clock.toggled.connect(self._update_rotate_frame)
        self.ui.rotate_anticlock.toggled.connect(self._update_rotate_frame)
        self.ui.rotate_flip.toggled.connect(self._update_rotate_frame)

        self._frame_count_set(self.frame_count)
        self._no_data_count_set(self.no_data_count)
        self.ui.amp_ch.setChecked(True)

        #  try loading last instance values
        try:
            f = open(init_values_file, 'r')
            init_values = json.loads(f.read())
            self._load_gui_values(init_values)
        except FileNotFoundError:
            self._no_init_values()

        self._recheck_values()

    ###################
    # 1. INIT #########
    ###################
    def _recheck_values(self):
        """
        In case loaded value is the same as
        the default value from the gui, the updata
        methods are not called and attributes not initiated.

        This is a workaround method which could be imporved.
        """
        self.motor_speed = self.ui.motor_speed.value()
        self.angle = self.ui.angle.value()
        self.motor_wait = self.ui.motor_wait_const.value()
        self.abs_pos = self.ui.abs_position.value()
        self.motor_steps = self.ui.motor_steps.value()
        self.n_sweeps = self.ui.n_sweeps.value()
        self.camera_port = self.ui.camera_port.value()
        self.frames_to_avg = self.ui.frames2avg.value()
        self.n_frames = self.ui.n_frames.value()
        self.accum_shots = self.ui.accum_shots.isChecked()
        self.live_recon = self.ui.live_recon.isChecked()
        self.live_recon_3d = self.ui.live_recon_3d.isChecked()
        self.save_opt = self.ui.save_opt.isChecked()
        self.radon_idx = self.ui.radon_idx.value()
        self.min_hist = self.ui.min_hist.value()
        self.max_hist = self.ui.max_hist.value()
        self.hot_std = self.ui.hot_pixel_std_multiple.value()
        self.corr_averages = self.ui.corr_averages.value()
        # line plot
        self.hline1_px = self.ui.hline1_px.value()
        self.hline2_px = self.ui.hline2_px.value()
        self.show_hlines = self.ui.show_hlines.isChecked()
        # toggle hist
        self.toggle_hist = self.ui.toggle_hist.isChecked()
        self.camera_type = self.ui.camera_type_list.currentIndex()
        self.motor_type = self.ui.motor_type_list.currentIndex()
        self.main_folder = self.ui.folder_path.toPlainText()
        self.rect = (self.ui.ulx.value(),
                     self.ui.uly.value(),
                     self.ui.brx.value(),
                     self.ui.bry.value())

    def _load_gui_values(self, d):
        """
        Load gui values if lif.json file exists.
        """
        try:
            self.append_history('Loading last instance values')
            self.ui.motor_speed.setValue(d['motor_speed'])
            self.ui.angle.setValue(d['angle'])
            self.ui.motor_wait_const.setValue(d['motor_wait'])
            self.ui.abs_position.setValue(d['abs_pos'])
            self.ui.motor_steps.setValue(d['motor_steps'])
            self.ui.n_sweeps.setValue(d['n_sweeps'])
            self.ui.camera_port.setValue(d['camera_port'])
            self.ui.frames2avg.setValue(d['frames_to_avg'])
            self.ui.n_frames.setValue(d['n_frames'])
            self.ui.accum_shots.setChecked(d['accum_shots'])
            self.ui.live_recon.setChecked(d['live_recon'])
            self.ui.live_recon_3d.setChecked(d['live_recon_3d'])
            self.ui.save_opt.setChecked(d['save_opt'])
            self.ui.radon_idx.setValue(d['radon_idx'])
            self.ui.min_hist.setValue(d['min_hist'])
            self.ui.max_hist.setValue(d['max_hist'])
            self.ui.hot_pixel_std_multiple.setValue(d['hot_std'])
            self.ui.corr_averages.setValue(d['corr_avgs'])
            self.ui.hline1_px.setValue(d['hline1_px'])
            self.ui.hline2_px.setValue(d['hline2_px'])
            self.ui.show_hlines.setChecked(d['show_hlines'])
            self.ui.toggle_hist.setChecked(d['toggle_hist'])
            self.ui.camera_type_list.setCurrentIndex(d['camera_type_idx'])
            self.ui.motor_type_list.setCurrentIndex(d['motor_type_idx'])
            self.ui.ulx.setValue(d['rect'][0])
            self.ui.uly.setValue(d['rect'][1])
            self.ui.brx.setValue(d['rect'][2])
            self.ui.bry.setValue(d['rect'][3])
            self.main_folder = d['folder_path']
            
        except KeyError:
            self.append_history('Not all init values found, loading defaults.')
            self._no_init_values()

        self._update_folder_path()

    def _save_gui_values(self):
        """
        Save last used values from the GUI into an
        lif.json file
        """
        vals = {}
        vals['motor_speed'] = self.motor_speed
        vals['angle'] = self.angle
        vals['motor_wait'] = self.motor_wait
        vals['abs_pos'] = self.abs_pos
        vals['motor_steps'] = self.motor_steps
        vals['n_sweeps'] = self.n_sweeps
        vals['camera_port'] = self.camera_port
        vals['frames_to_avg'] = self.frames_to_avg
        vals['n_frames'] = self.n_frames
        vals['accum_shots'] = self.accum_shots
        vals['live_recon'] = self.live_recon
        vals['live_recon_3d'] = self.live_recon_3d
        vals['save_opt'] = self.save_opt
        vals['radon_idx'] = self.radon_idx
        vals['min_hist'] = self.min_hist
        vals['max_hist'] = self.max_hist
        vals['hot_std'] = self.hot_std
        vals['corr_avgs'] = self.corr_averages
        vals['hline1_px'] = self.hline1_px
        vals['hline2_px'] = self.hline2_px
        vals['show_hlines'] = self.show_hlines
        vals['toggle_hist'] = self.toggle_hist
        vals['camera_type_idx'] = self.camera_type
        vals['motor_type_idx'] = self.motor_type
        vals['folder_path'] = self.main_folder
        vals['rect'] = (self.ui.ulx.value(),
                        self.ui.uly.value(),
                        self.ui.brx.value(),
                        self.ui.bry.value())
        with open(self.init_file, 'w') as f:
            f.write(json.dumps(vals))

    def _no_init_values(self):
        """
        In case of no lif.json file, fill the
        default values
        """
        self.ui.motor_speed.setValue(400)
        self.ui.angle.setValue(400)
        self.ui.motor_wait_const.setValue(0.002)
        self.ui.abs_position.setValue(100)
        self.ui.motor_steps.setValue(4)
        self.ui.n_sweeps.setValue(1)
        self.ui.camera_port.setValue(1)
        self.ui.frames2avg.setValue(10)
        self.ui.n_frames.setValue(10)
        self.ui.accum_shots.setChecked(False)
        self.ui.live_recon.setChecked(False)
        self.ui.live_recon_3d.setChecked(False)
        self.ui.save_opt.setChecked(True)
        self.ui.radon_idx.setValue(10)
        self.ui.min_hist.setValue(1)
        self.ui.max_hist.setValue(250)
        self.ui.hot_pixel_std_multiple.setValue(7)
        self.ui.corr_averages.setValue(30)
        self.ui.hline1_px.setValue(100)
        self.ui.hline2_px.setValue(1800)
        self.ui.show_hlines.setChecked(False)
        self.ui.toggle_hist.setChecked(False)
        self.ui.camera_type_list.setCurrentIndex(0)
        self.ui.motor_type_list.setCurrentIndex(0)
        self.main_folder = os.getcwd()
        self.ui.ulx.setValue(0)
        self.ui.uly.setValue(1)
        self.ui.brx.setValue(1)
        self.ui.bry.setValue(0)
        self._update_folder_path()

    ######################################
    # 2. UI interfacing ##################
    ######################################
    def _update_rect(self):
        self.rect = (self.ui.ulx.value(),
                     self.ui.uly.value(),
                     self.ui.brx.value(),
                     self.ui.bry.value())

        # no plotting of the rectangle, uncomment if in use
        # self.replot_rectangle()

    def _update_hot_std_mult(self):
        self.hot_std = self.ui.hot_pixel_std_multiple.value()

    def _update_corr_averages(self):
        self.corr_averages = self.ui.corr_averages.value()

    def _update_hor_cut_pxs(self):
        self.hline1_px = self.ui.hline1_px.value()
        self.hline2_px = self.ui.hline2_px.value()

    def _update_show_hlines(self):
        self.show_hlines = self.ui.show_hlines.isChecked()

    def _update_camera_port(self):
        """
        Update camera port from the GUI,
        TODO Option for user to identify her camera
        """
        self.camera_port = self.ui.camera_port.value()

    def _show_camera_settings(self):
        if not self.camera_on:
            self.message_text(
                "Initialize CAMERA first."
            )
            return

        d = self.camera.get_settings()
        self.message_display_dict(d)

    def _update_hist_min(self):
        """
        Set minimum level for main image histogram
        from GUI
        """
        self.min_hist = self.ui.min_hist.value()
        self._check_hist_vals()

    def _update_hist_max(self):
        """
        Set maximum level for main image
        histogram from GUI
        """
        self.max_hist = self.ui.max_hist.value()
        self._check_hist_vals()

    def _check_hist_vals(self):
        """
        Check if min hist is lower than hist max
        Raise error message and set the min/max below or above
        respectively
        """
        if self.max_hist is None or self.min_hist is None:
            return
        if self.ui.max_hist.value() <= self.ui.min_hist.value():
            self.message_text(
                "'Min hist' value has to be lower than 'Max hist'"
            )
            self.ui.max_hist.setValue(self.min_hist+1)

    def _update_toggle_hist(self):
        """
        Use histogram min/max levels for the main images
        intensity range if toggled
        """
        self.toggle_hist = self.ui.toggle_hist.isChecked()

    def _update_folder_path(self):
        """
        Update saving folder path from GUI
        """
        self.ui.folder_path.setText(self.main_folder)

    def _update_radon_idx(self):
        """
        Which horizontal line (index) of the main image
        will be reconstructed.

        Updated from the GUI.
        """
        self.radon_idx = self.ui.radon_idx.value()
        self.replot_recon_line()

    def _update_live_recon_btn(self):
        """
        If GUI button checked, live reconstruction is active
        during the experiment.
        """
        self.live_recon = self.ui.live_recon.isChecked()

    def _update_live_recon_3d_btn(self):
        self.live_recon_3d = self.ui.live_recon_3d.isChecked()

    def _update_save_opt(self):
        self.save_opt = self.ui.save_opt.isChecked()

    def _update_camera_channels(self, checked):
        """
        Checks which camera channel is selected
        in the GUI.

        Args:
            checked (bool): True value for a checked button
        """
        if checked:
            return
        if self.ui.red_ch.isChecked():
            self.append_history('red channel only detection')
            self.channel = 0
        elif self.ui.green_ch.isChecked():
            self.append_history('green channel only detection')
            self.channel = 1
        elif self.ui.blue_ch.isChecked():
            self.append_history('blue channel only detection')
            self.channel = 2
        elif self.ui.amp_ch.isChecked():
            self.append_history('all channels detection')
            self.channel = 3

        if self.camera_on:
            self.camera.col_ch = self.channel
        print(self.channel)
        return

    def _update_rotate_frame(self, checked):
        if checked:
            return
        if self.ui.no_rotate.isChecked():
            self.rotate = 'no'
        elif self.ui.rotate_clock.isChecked():
            self.rotate = 'clock'
        elif self.ui.rotate_anticlock.isChecked():
            self.rotate = 'anticlock'
        elif self.ui.rotate_flip.isChecked():
            self.rotate = 'flip'

        if self.camera_on:
            self.append_history(f'changing rotate setting to {self.rotate}.')
            self.camera.rotate = self.rotate
        return

    def _update_accum_shots(self):
        """
        If checked, shots are getting accumulated and not
        averaged. Effect is immediate if acquiring.

        Careful with the output data size, because frames do
        not fit into jpg format any more.
        """
        self.accum_shots = self.ui.accum_shots.isChecked()
        if self.camera_on:
            self.append_history(
                'Accumulate shots: '
                + str(self.ui.accum_shots.isChecked())
                )
            self.camera.accum = self.ui.accum_shots.isChecked()

    def _update_motor_steps(self):
        """
        Update number of motor steps per move (step)
        from GUI
        """
        self.motor_steps = self.ui.motor_steps.value()

    def _update_n_sweeps(self):
        """
        Update number of sweeps, i.e. repetitions of the
        one revolution OPT scan
        """
        self.n_sweeps = self.ui.n_sweeps.value()

    def _update_n_frames(self):
        """
        Update from GUI how many frames to aquire per
        step of the OPT experiment or with a live acquisition
        mode.

        Does not take into account averaging per frame.
        """
        self.n_frames = self.ui.n_frames.value()

    def _update_camera_type(self):
        """
        Update camera type from GUI
        TODO: initialization of the camera to be triggered by
        separate button
        """
        self.camera_type = self.ui.camera_type_list.currentIndex()

    def _update_motor_type(self):
        """
        Update motor type from the dropdown menu
        in the GUI
        """
        self.motor_type = self.ui.motor_type_list.currentIndex()
        if self.motor_type == 0:
            self.motor = 'Uno-stepper'
        elif self.motor_type == 1:
            self.motor = 'nanotec'
        else:
            raise ValueError

    def _update_frame_rate(self):
        """
        Update frame rate from the GUI. Not available
        for the cheap cameras
        """
        self.frame_rate = self.ui.frame_rate.value()

    def _update_frames_to_avg(self):
        """
        Number of frames to average into a single frame
        """
        self.frames_to_avg = self.ui.frames2avg.value()

    def _update_motor_speed(self):
        """
        Update motor speed from the GUI
        """
        self.motor_speed = self.ui.motor_speed.value()
        if self.motor_on:
            self.append_history('updating motor speed')
            self.stepper.set_speed(self.motor_speed)

    def _update_motor_angle(self):
        """
        Update motor angle to turn in stepping mode
        For Uno-stepper.

        2048 steps signify a full turn.
        """
        self.angle = self.ui.angle.value()

    def _update_motor_wait(self):
        """
        Update wait constant (in s) for the motor stepping.
        Too small might be dangerous because of threading
        and also vibrations of the sample.
        """
        self.motor_wait = self.ui.motor_wait_const.value()
        if self.motor_on:
            self.stepper.set_wait_const(self.motor_wait)

    def _update_abs_pos(self):
        """
        Update where is set the absolute position for
        the stepper move.
        """
        self.abs_pos = self.ui.abs_position.value()

    def _update_metadata_expr(self):
        """
        Update metadata from the UI text box.
        TODO: Make sure parsing works for various inputs
        """
        self.metadata['exp_notes'] = self.ui.expr_metadata.toPlainText()

    ####################################
    # 3. EXECUTE BUTTONS ###############
    ####################################
    def exec_flat_field(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Unblock Camera")
        text = "Only for transmission mode.\
            You should have flat field illumination\
            within the linear regime. Acquisition will\
            perform 100x average at current exposure time.\
            The same as for dark-field."
        msg.setInformativeText(" ".join(text.split()))
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        btn_measure = msg.button(QtWidgets.QMessageBox.Ok)
        btn_measure.setText('Acquire with current setting?')
        msg.buttonClicked.connect(
            partial(
                self.acquire_correction,
                corr_type='flat_field',
                averages=100))
        retval = msg.exec_()
        return retval

    def exec_hot_pixels(self):
        """
        Block camera message before acquisition
        of the dark-field counts, used for identification
        of hot pixels. This is separate operation from dark
        field correction.

        Returns:
            int: sys execution status.
        """
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Block Camera")
        text = "Reinitialize camera with maximum exposure time possible.\
            Saved frame is a frame averaged 20x. Hot pixels will \
            be identified as intensity higher than 5x STD, and their count \
            shown for reference"
        msg.setInformativeText(" ".join(text.split()))
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        btn_measure = msg.button(QtWidgets.QMessageBox.Ok)
        btn_measure.setText('Acquire with current setting?')
        msg.buttonClicked.connect(
            partial(
                self.acquire_correction,
                corr_type='hot_pixels',
                averages=20))
        retval = msg.exec_()
        return retval

    def exec_dark_field(self):
        """
        Block camera message before acquisition
        of the dark-field counts, used for identification
        of hot pixels. This is separate operation from dark
        field correction.

        Returns:
            int: sys execution status.
        """
        averages = 30
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Block Camera")
        text = f"Acquire does {averages} averages at current exposure time.\
            Exposure time MUST be the same as for the\
            experiment you are going to perform."
        msg.setInformativeText(" ".join(text.split()))
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        btn_measure = msg.button(QtWidgets.QMessageBox.Ok)
        btn_measure.setText('Acquire NOW?')
        msg.buttonClicked.connect(
            partial(
                self.acquire_correction,
                corr_type='dark_field',
                averages=averages))
        retval = msg.exec_()
        return retval

    def linearity_calibration(self):
        """
        Load calibration file, doing it alone is tedious,
        can be suggested to user

        TODO: This should be done once, saved and know
        for each camera what is the linear range.
        """
        raise NotImplementedError

    def snap_dmk(self):
        if not self.camera_on:
            self.message_text(
                "Initialize CAMERA first."
            )
            return
        # these two lines is just a workaround
        self.ui.n_frames.setValue(1)
        self.ui.frames2avg.setValue(1)

        if self.camera.camera_ready():
            self.camera.snap_image()
            self.post_acquire(self.camera.current_img, 0)
        else:
            self.append_history('Unknown problem, camera')

    def exec_get_n_frames_btn(self):
        """
        Button triggers acquisition of self.n_frames
        frames, each averaged or accumulated.

        In case of OPT acquisition, all these frames
        will be saved at each angle (motor step).
        """
        # check camera
        if not self.camera_on:
            self.message_text(
                "Initialize CAMERA first."
            )
            return
        self._frame_count_set(0)
        self._no_data_count_set(0)
        self.acquire()

    def exec_save_image_btn(self):
        name = self.ui.filename.toPlainText()+self.get_time_now()
        self.save_image(name)

        # if not initialized, do it here
        if not self.motor_on:
            self.message_text("Initialize MOTOR first")
            raise NoMotorInitialized

        self.ui.angle.setValue(
            int(self.stepper.full_rotation / self.motor_steps)
        )
        self.append_history(f'ANGLE: {self.angle}')

    def exec_show_3d_btn2(self):
        print('Not implemented yet')
        return

    def exec_show_3d_btn(self):
        print('Not implemented yet')

    def _set_opt_step(self):
        if not self.motor_on:
            raise NoMotorInitialized

        if self.stepper.full_rotation % self.motor_steps:
            self.append_history('Whole division of full rotation by\
                                number of steps not possible')
            raise ValueError('wrong number of steps')
        else:
            self.append_history(
                f'angle set to {self.stepper.full_rotation // self.motor_steps} steps.')
            self.ui.angle.setValue(
                self.stepper.full_rotation // self.motor_steps
                )

    def exec_run_opt_btn(self):
        """
        Triggers OPT execution.

        1. Creates saving folder.
        2. Disable buttons.
        3. Check motor, collect metadata
        4. Call :fun:`Gui.run_sweep`_.
        """
        self.create_saving_folder()

        self._check_motors()
        if not self.simul_mode:
            self._set_opt_step()

        self.collect_metadata()
        self.metadata['sweep_start'] = []
        self.metadata['sweep_finish'] = []
        self.metadata['sweep_start'].append(self.get_time_now())
        self.ui.progressBar.setValue(0)
        self.sweep_count_set(0)
        self.disable_btns()
        self.opt_running = True
        self.run_sweep()

    def exec_start_cont_opt(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Acquire continuous OPT NOW?")
        text = "Pressing OK will start continuous motor rotation \
            and 1 sec after continuous snapping of the camera frames\
            1. Synchronization does not exist. 2. No averaging.\
            3. Stop manually."
        msg.setInformativeText(" ".join(text.split()))
        msg.setStandardButtons(
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msg.buttonClicked.connect(self.acquire_cont_opt)
        retval = msg.exec_()
        return retval

    def exec_stop_cont_opt(self):
        self.stop_opt = True

    def exec_motor_close_btn(self):
        """
        Close the stepper by shutting down the
        arduino board connection.

        Disable/enable motor initiation buttons.
        """
        try:
            self.stepper.shutdown()
            self.motor_thread.quit()
        except Exception as e:
            self.append_history(f'Problem closing motor, {e}')
        else:
            self.ui.motor_init_btn.setDisabled(False)
            self.ui.motor_close_btn.setDisabled(True)

    def exec_step_motor_btn(self):
        """
        Move a stepper motor with self.speed and by
        self.angle.

        In simul mode (virtual camera), nothing will happen.
        """
        if self.simul_mode:
            self.append_history('simul mode, no rotation enabled')
            return
        self.append_history(f'motor speed: {self.stepper.speed}')

        self.stepper.move_relative(self.angle)
        self._current_motor_position(self.stepper.get_position())

    def exec_step_abs_btn(self):
        """
        Move a stepper motor with self.speed and by
        self.angle.

        In simul mode (virtual camera), nothing will happen.
        """
        if self.simul_mode:
            self.append_history('simul mode, no rotation enabled')
            return
        self.append_history(f'motor speed: {self.stepper.speed}')
        self.stepper.move_absolute(self.abs_pos)
        self._current_motor_position(self.stepper.get_position())

    def exec_rotate_cont_btn(self):
        """
        Continuous rotation of a motor.

        TODO: Necessary to fix the parallel threading
        to be able to acquire while rotating.
        """
        self.stepper.start_cmove()

    def exec_stop_rotate_cont_btn(self):
        self.stepper.stop_moving()
        self._current_motor_position(self.stepper.get_position())

    def select_folder(self):
        """
        Opens a folder selection dialog to choose
        data saving folder. Folder path also displayed in
        the textbox.
        """
        folder = str(QtWidgets.QFileDialog.getExistingDirectory(
                                self, "Select Directory"))
        if not folder:
            self.append_history('no change in data folder')
            return

        self.main_folder = folder
        self._update_folder_path()  # sets path to textbox
        self.append_history('new data folder selected')

    def exec_stop_btn(self):
        """
        Stops acquisition, close camera, acquire and
        motor threads.
        """
        self.append_history('Stopped')
        self.stop_request = True
        if self.opt_running:
            self.post_opt()

        try:
            self.camera.exit()
            self.acquire_thread.quit()
            self.camera_on = False
        except Exception as e:
            print(f'problem closing acquire thread: {e}')
        if self.motor_on:
            self.exec_motor_close_btn()
            # self.stepper.shutdown()
            # self.motor_thread.quit()
        self.stop_request = False

    def exec_exit_btn(self):
        """
        Exit GUI including safeguarding
        in case exit is called before stop.
        """
        self.append_history('Stopped')

        if self.idle is False:
            self.finish()

        self._save_gui_values()
        self.close()

    #################################
    # 4. Initialize HW ##############
    #################################
    def exec_motor_init_btn(self):
        """
        Initialize stepper motor. Raise errors
        if failed. If successful, set motor_on to True.

        1. 'Initialize' button disable.
        2. 'Close motor' button enable.
        """
        try:
            self.initialize_stepper()
        except NoMotorInitialized:
            self.append_history('No motor found.')
        except Exception as e:
            self.append_history(f'Motor problem, {e}.')
        else:
            self.motor_on = True
            self.ui.motor_init_btn.setDisabled(True)
            self.ui.motor_close_btn.setEnabled(True)
            self.append_history('motor ready.')

    def initialize_stepper(self):
        """Initialize a stepper motor.

        1. Create motor thread.
        2. Initialize or raise exception.
        3. Move the stepper to the thread.
        """
        self.motor_thread = QtCore.QThread(parent=self)
        self.motor_thread.start()
        try:
            print(self.motor)
            self.stepper = Stepper(self.motor,
                                   speed=self.motor_speed,
                                   wait_const=self.motor_wait)
        except NoMotorInitialized:
            self.append_history('No motor exception raised.')
            self.ui.motor_init_btn.setDisabled(False)
        except Exception as e:
            self.append_history(f'Unknown motor problem: {e}.')
            self.ui.motor_init_btn.setDisabled(False)
        self.stepper.moveToThread(self.motor_thread)

    def _check_motors(self):
        """
        Checking the stepper motor before the OPT acquisition
        starts.

        1. Set step count to 0, and unit of progress for \
            sweep progress bar.
        2. In case of virtual camera, exit method.
        3. Initialize motor, if not already.
        """
        self.unit_of_progress = 100/self.motor_steps
        self.step_count = 0

        # for virtual camera, no need for a motor
        if self.simul_mode:
            return

    def initialize_camera(self):
        """
        Initialize camera.
        TODO: try to force resolution of the low-end
        cameras

        In case some camera is already initialized, the
        thread will be killed and re-initialized again.
        """
        self.append_history('Initializing camera')

        # if camera on, quit current thread
        if self.camera_on:
            self.acquire_thread.quit()

        # initialize
        self.img_format = 'np.int8'
        self.ui.motor_steps.setEnabled(True)
        if self.camera_type == 0:
            # virtual
            self.initialize_virtual_camera()
            self.ui.motor_steps.setValue(self.simul_angles)
            self.ui.motor_steps.setDisabled(True)
        elif self.camera_type == 1:
            # Sky_basic
            self.resolution = (1280, 720)
            self.initialize_sky_basic()
        elif self.camera_type == 2:
            # phonefix
            self.resolution = (1920, 1080)
            self.initialize_phonefix()
        elif self.camera_type == 3:
            self.initialize_dmk()
            if self.camera.format == 4:
                self.img_format = 'np.int16'

        self.camera_on = True
        # create and connect camera.acquire thread
        self.acquire_thread = QtCore.QThread(parent=self)
        self.acquire_thread.start()
        self.camera.moveToThread(self.acquire_thread)
        self.camera.start_acquire.connect(self.camera.acquire)
        self.camera.data_ready.connect(self.post_acquire)

    def initialize_dmk(self):
        self.simul_mode = False
        try:
            ret = self.camera.camera_ready()
            if ret:
                self.camera.exit()
        except AttributeError:
            pass
        self.camera = DMK("DMK 37BUX252", self.rotate)
        wid = self.ui.stream.winId()
        self.camera.startCamera(wid)
        self.append_history('camera on')
        self.camera_on = True

    def initialize_sky_basic(self):
        """
        Initialize Sky basic camera on a given
        port, color channel and resolution.
        """
        self.simul_mode = False
        self.camera = Sky_basic(
                            channel=self.camera_port,
                            col_ch=self.channel,
                            resolution=self.resolution,
                            bin_factor=1
                            )

    def initialize_phonefix(self):
        """
        Initialize the phonefix camera on a given
        port, color channel and resolution.
        """
        self.simul_mode = False
        self.append_history('this camera can take longer to INIT')
        self.camera = Phonefix(
                            channel=self.camera_port,
                            col_ch=self.channel,
                            res=self.resolution,
                            )

    def initialize_virtual_camera(self):
        """
        Initialize virtual camera, which requires generating
        sinogram from the 3D shepp phantom data.

        TODO: This takes time and causes crashes of the tests
        on the github actions. Therefore will be triggered by
        camera initialize button.
        """
        print('initializing virtual camera')
        self.simul_mode = True
        self.camera = Virtual(self.simul_angles)

    #######################
    # 5. Counters #########
    #######################
    def _frame_count_set(self, count):
        """
        Update frame count in the current
        acquisition run. Frame count is dispalyed
        in the QLCD GUI object.

        Args:
            count (int): Frame number
        """
        self.frame_count = count
        self.ui.frame_count.display(self.frame_count)

    def _current_motor_position(self, pos):
        self.motor_pos = pos
        self.ui.current_pos.display(self.motor_pos)

    def _no_data_count_set(self, count):
        """
        Update count of frames which has not been received
        form the camera in the current run.

        NO data count displayed in the QLCD GUI object.

        Args:
            count (int): Number of NO data frames.
        """
        self.no_data_count = count
        self.ui.no_data_count.display(self.no_data_count)

    def sweep_count_set(self, count):
        """
        Update sweep count during OPT acquisition.
        Count displayed in QLCD display in the GUI.

        Args:
            count (int): sweep number
        """
        self.sweep_count = count
        self.ui.sweep_count.display(self.sweep_count)

    def disable_btns(self):
        """
        Disable buttons during the OPT acquisition.

        TODO: if acquisition raises errors, GUI needs to go
        to a default state.
        """
        self.ui.stepper_box.setDisabled(True)
        self.ui.camera_box.setDisabled(True)
        self.ui.acquire_settings_box.setDisabled(True)
        self.ui.measure_box.setDisabled(True)

    def enable_btns(self):
        """
        Enable buttons after the OPT experiment is over.
        """
        self.ui.stepper_box.setDisabled(False)
        self.ui.camera_box.setDisabled(False)
        self.ui.acquire_settings_box.setDisabled(False)
        self.ui.measure_box.setDisabled(False)

    def clear_sweep_data(self):
        """
        Clear sweep data before the next swepp
        start.

        TODO: clear also a reconstruction image.
        """
        self.current_frame = None
        self.current_recon = None
        self.step_count = 0

    def collect_metadata(self):
        """
        Collect metadata, N steps, N sweep,
        averages per frame, frames per steps,
        camera dynamic range, experiment notes.
        """
        self.metadata['n_steps'] = self.motor_steps
        self.metadata['n_sweeps'] = self.n_sweeps
        self.metadata['avg_per_frame'] = self.frames_to_avg
        self.metadata['images_per_step'] = self.n_frames

        if self.camera_type in [0, 1]:
            self.metadata['dynamic_range'] = 'np.int8'
        self.metadata['user notes'] = self.ui.expr_metadata.toPlainText()

    def save_metadata(self):
        """
        Saving metadata dictionary in json format into the
        data saving folder.
        """
        file_path = os.path.join(self.exp_path, 'metadata.txt')
        with open(file_path, 'w') as f:
            f.write(json.dumps(self.metadata))

    def run_sweep(self):
        """
        Calls get_n_frames()
        TODO: split exec_btn and get_n_frames
        """
        self.append_history(f'STEP {self.step_count}')
        self.exec_get_n_frames_btn()

    def save_image(self, fname=None):
        """
        Saving frames as images or text files (in case accum shots
        is selected), which results in float numbers.

        1. Create filename. Default file name is sweep_step_frame \
        numbers separated by '_'.
        2. If saving folder does not exist, create it.
        3. If/else for averaging vs accumulation of the frames modes.

        Args:
            fname (str, optional): file name, used in cases of
            saving calibrations etc. Defaults to None.
        """
        if not fname:
            fname = '_'.join([str(self.sweep_count),
                              str(self.step_count),
                              str(self.frame_count)])
        if not self.exp_path:
            self.create_saving_folder()

        ############################################
        # Casting now happens on the acquire level #
        ############################################
        
        # print(f'frame format: {type(self.current_frame.frame)}')
        # to_save = self.current_frame.frame.astype(eval(self.img_format))
        # print(f'to_save format: {type(to_save)}')

        if self.accum_shots:
            file_path = os.path.join(self.exp_path, fname+'.txt')
            np.savetxt(file_path, self.current_frame.frame)
        else:
            print(f"saving {fname + '.tiff'} in {self.img_format} format.")
#             print(f'counts of Frame: {np.amax(self.current_frame.frame)}, \
# mean counts: {np.mean(self.current_frame.frame)}')
#             print(f'std counts: {np.std(self.current_frame.frame)}')
#             print('HISTOGRAM')
#             print(np.histogram(self.current_frame.frame))
            file_path = os.path.join(self.exp_path, fname+'.tiff')
            cv2.imwrite(file_path, self.current_frame.frame)

    ##########################
    # 6. ACQUISITION #########
    ##########################
    def acquire(self):
        """
        Acquire data from camera
        1. Set how much averaging to do for single frames
        2.
        3. Emit start_acquire thread data

        TODO: Get rid of camera.idx part.
        """
        self.camera.set_average(self.frames_to_avg)
        # only needed for the virtual camera
        if self.opt_running:
            self.camera.idx = self.step_count
        else:
            self.camera.idx = self.frame_count
        self.camera.start_acquire.emit()

    post_ac_ready = QtCore.pyqtSignal(bool)

    @QtCore.pyqtSlot(np.ndarray, int)
    def post_acquire(self, frame, no_frame_count):
        """Data handling after receiving data form the camera.
        1. Update current frame attribute
        2. Update plots
        3. Check stop request, save data
        4. Update frame count.
        5. If all frames form current step done, move to \
        the next step. Otherwise, acquire again.

        Args:
            frame (ndarray): Averaged current frame.
            no_frame_count (int): No data received count.
        """
        try:
            self.current_frame.update_frame(frame, no_frame_count)
        except AttributeError:
            print('current_frame does not exist, creating a new one.')
            self.current_frame = Data(frame, no_frame_count, self.img_format)

        self.current_frame_plot()
        self.current_hlines_plot()

        # check is stop is requested
        if self.stop_request is True:
            self.finish()

        if self.stop_opt is True:
            self.post_cont_opt()

        # saving
        if self.opt_running and self.save_opt:
            self.save_image()

        if self.cont_opt and self.save_opt:
            self.save_image(f'{self.frame_count:04d}')

        self._frame_count_set(self.frame_count+1)
        self.post_ac_ready.emit(True)
        # checking for end of current step
        if self.frame_count >= self.n_frames:
            if self.opt_running:
                self.post_step()
            else:
                self.idling()
        else:
            self.acquire()

    def post_step(self):
        """After all frames of the current step are processed,
        update progress bar, update reconstruction plot
        2. If last step of the sweep -> post_sweep()
        3. Otherwise step motor and acquire data again \
        by calling run_sweep method.
        """
        self.ui.progressBar.setValue(
                int((self.step_count+1)*self.unit_of_progress))
        if self.live_recon:
            self.update_recon()
            self.current_recon_plot()

        if self.live_recon_3d:
            self.update_recon_3d()

        if self.step_count == self.motor_steps-1:
            self.post_sweep()
        else:
            self.step_count += 1
            self.exec_step_motor_btn()
            self.run_sweep()

    def post_sweep(self):
        """
        Processing after a sweep is finished.

        1. Register time of sweep finish, add to metadata.
        2. If last sweep, close experiment with post_opt()
        3. Otherwise go to next sweep via run_sweep()
        """
        self.metadata['sweep_finish'].append(self.get_time_now())
        self.sweep_count_set(self.sweep_count + 1)
        if self.sweep_count == self.n_sweeps:
            self.post_opt()
        else:
            self.clear_sweep_data()
            self.run_sweep()

    def post_opt(self):
        """Steps after OPT experiment acquisition finished.

        1. Save metadata.
        2. Enable buttons.
        3. Clear sweep data.
        4. Go to idling() state.
        """
        self.save_metadata()
        if self.save_opt:
            try:
                np.save('test.npy', self.recon_3d.output)
            except AttributeError:
                self.append_history('No 3D reconstruction to save.')

        self.enable_btns()
        self.opt_running = False
        self.clear_sweep_data()
        self.idling()

    def acquire_cont_opt(self, btn):
        print(btn.text())
        if btn.text() != 'OK':
            return

        # set acquisition values
        self._frame_count_set(0)
        self._no_data_count_set(0)
        self.ui.n_frames.setValue(1000)
        self.ui.frames2avg.setValue(1)
        self.cont_opt = True

        self.create_saving_folder()
        # self.disable_btns()

        # start the motor
        print(self.stepper.speed, self.stepper.max_speed)
        self.stepper.max_speed = self.motor_speed
        print(self.stepper.speed, self.stepper.max_speed)

        self.exec_rotate_cont_btn()
        sleep(1)

        # start acquisition
        self.acquire()

    def post_cont_opt(self):
        self.exec_stop_rotate_cont_btn()
        self.save_metadata()

        # this line is a workaround to stop snapping images
        self.ui.n_frames.setValue(1)
        self.cont_opt = False
        self.stop_opt = False

    def acquire_correction(self, btn, corr_type, averages):
        if btn.text() == 'Cancel':
            return

        # check if camera on
        if not self.camera_on:
            self.message_text(
                "Initialize CAMERA first."
            )
            return

        # other option is to acquire dark counts.
        self.ui.n_frames.setValue(1)
        self.ui.frames2avg.setValue(averages)
        self.post_ac_ready.connect(
            partial(self._continue, corr_type=corr_type),
            )
        self.exec_get_n_frames_btn()

    def _continue(self, corr_type):
        exec(f'self.{corr_type} = self.current_frame.frame')

        # saving
        file_name = corr_type + self.get_time_now()
        self.save_image(file_name)
        self.append_history(corr_type + ' correction saved.')

        # process hot pixel acquisition
        if corr_type == 'hot_pixels':
            self.process_hot_pixels()
        elif corr_type == 'dark_field':
            self.process_dark_field()
        elif corr_type == 'flat_field':
            self.process_flat_field()
        else:
            raise ValueError
        self.post_ac_ready.disconnect()

    def process_hot_pixels(self):
        std = np.std(self.hot_pixels, dtype=np.float64)
        mean = np.mean(self.hot_pixels, dtype=np.float64)
        # hot_std is the cutoff
        hot_vals = self.hot_pixels[self.hot_pixels > (mean + self.hot_std*std)]
        hot = np.ma.masked_greater(self.hot_pixels, mean + self.hot_std*std)

        self.ui.hot_count.display(len(hot_vals))
        self.ui.hot_mean.display(np.mean(hot_vals))
        self.ui.nonhot_mean.display(np.mean(hot))

    def process_dark_field(self):
        self.ui.dark_mean.display(np.mean(self.dark_field))
        self.ui.dark_std.display(np.std(self.dark_field))

    def process_flat_field(self):
        self.ui.flat_mean.display(np.mean(self.flat_field))
        self.ui.flat_std.display(np.std(self.flat_field))

    ##################################
    # 7. Metadata, saving, reporting #
    ##################################
    def get_date_now(self):
        """Get current date and time which is
        used for the experimental metadata information

        Returns:
            str: datetime from years to seconds
        """
        return strftime("%y%m%d-%H-%M-%S", gmtime())

    def get_time_now(self):
        """Get current time string, used for experimental
        metadata information.

        Returns:
            str: time H-M-S
        """
        return strftime('%H-%M-%S', gmtime())

    def create_saving_folder(self):
        """Create experiment saving folder in the data saving folder
        selected by user in the GUI. Method updates path attribute.
        Name of the folder is a datetime string.

        1. Create the folder and report in the history tab

        Folder name is not optional and has unified format.
        """
        self.exp_path = os.path.join(self.main_folder,
                                     self.get_date_now(),
                                     )
        os.mkdir(self.exp_path)
        self.append_history(f'created dir: {self.exp_path}')

    def append_history(self, message):
        """Append history tab with runtime messages to user

        Args:
            message (str): Message as a single string.
        """
        self.ui.history.appendPlainText(message)

    ####################################
    # 8. PLOTTING ######################
    ####################################
    def update_recon(self):
        """
        Update Radon reconstruction after OPT step is finished.
        Handles if the reconstruction index is too high.

        TODO: handle that exception better. Experiment should continue
        without reconstruction
        """
        try:
            self.current_recon.update_recon(
                self.current_frame.frame[self.radon_idx, :],
                self.step_count)
        except AttributeError:
            try:
                print('Creating a new reconstruction object.')
                self.current_recon = Radon(
                    self.current_frame.frame[self.radon_idx, :],
                    self.motor_steps)
            except IndexError as e:
                self.append_history('Reconstruction index too high')
                # TODO save to looger
                print(e)
                self.post_opt()

    def update_recon_3d(self):
        try:
            self.recon_3d.update_recon(
                self.current_frame.frame[self.rect[1]:self.rect[3],
                                         self.rect[0]:self.rect[2]],
                self.step_count,
            )
        except AttributeError:
            try:
                print('Creating new 3D recon object')
                self.recon_3d = Radon(
                    self.current_frame.frame[self.rect[1]:self.rect[3],
                                             self.rect[0]:self.rect[2]],
                    self.motor_steps,
                )
            except IndexError as e:
                print(e)
                self.post_opt()

    def create_plots(self):
        """
        Creates plots during the GUI initialization processes
        And defines defaults for each graph

        1. Camera image plot is a pyqtgraph histogram widget
        2. Reconstruction plot is a pyqtgraph plotItem
        """
        self.hist = self.ui.camera_live.getHistogramWidget()
        self.hist.fillHistogram(color=(255, 0, 0))

        self.ui.recon_live.plotItem.setLabels(
            left='pixel Y',
            bottom='pixel X'
        )

        self.rect_plot = None
        self.line_plot = None

    def current_frame_plot(self):
        """
        Update current frame plot. Or raise exception.
        """
        try:
            self.ui.camera_live.setImage(np.rot90(self.current_frame.frame))
            # self.ui.camera_live.setLabel(axis='left', text='Y-axis')
            self.ui.camera_live.ui.splitter.setSizes([1, 1])
            if self.toggle_hist:
                self.hist.setLevels(
                    min=self.min_hist,
                    max=self.max_hist,
                )

        except Exception as e:
            self.append_history(f'Error Plotting Last Frame, {e}')
        return
    
    def current_hlines_plot(self):
        if self.show_hlines is False:
            return
        
        print(self.current_frame.frame.shape, self.hline1_px, self.hline2_px)

        pen1 = pg.mkPen(color=(255, 0, 0))
        pen2 = pg.mkPen(color=(0, 0, 255))
        self.ui.hor_cut_plot.clear()
        self.ui.hor_cut_plot.plot(self.current_frame.frame[self.hline1_px],
                                  pen=pen1)
        self.ui.hor_cut_plot.plot(self.current_frame.frame[self.hline2_px],
                                  pen=pen2)

    def replot_rectangle(self):
        camera_v = self.ui.camera_live.getView()
        if self.rect_plot:
            camera_v.removeItem(self.rect_plot)

        self.rect_plot = pg.PlotCurveItem(
            x=[self.rect[0],
               self.rect[2],
               self.rect[2],
               self.rect[0],
               self.rect[0]],
            y=[self.rect[1],
               self.rect[1],
               self.rect[3],
               self.rect[3],
               self.rect[1]],
            pen=pg.mkPen(width=3, color='b'))
        camera_v.addItem(self.rect_plot)

    def replot_recon_line(self):
        camera_v = self.ui.camera_live.getView()
        if self.line_plot:
            camera_v.removeItem(self.line_plot)

        self.line_plot = pg.PlotCurveItem(
            y=[self.radon_idx, self.radon_idx],
            pen=pg.mkPen(width=3, color='r'))
        camera_v.addItem(self.line_plot)

    def current_recon_plot(self):
        """
        Update reconstruction image based on the current last frame.
        """
        try:
            img = pg.ImageItem(image=self.current_recon.output)
            self.ui.recon_live.plotItem.addItem(
                img,
                clear=True,
                pen='b'
            )
        except Exception as e:
            self.append_history(f'Error Plotting Last Recon, {e}')
        return

    ######################
    # 9. STATE methods ###
    ######################
    def idling(self):
        """
        Idle state
        """
        if self.cont_opt:
            self.post_cont_opt()

        self.idle = True

    def finish(self):
        """
        First idle state and then quit threads, both
        stepper, camera and acquire threads.
        """
        self.idling()
        self.acquire_thread.quit()
        if self.motor_on:
            self.stepper.shutdown()
            self.motor_thread.quit()
        try:
            self.camera.exit()
        except Exception as e:
            self.append_history(f'camera.exit() problem: {e}')
            pass

    ########################
    # 10. MESSAGES ##########
    ########################
    def message_text(self, text):
        """
        Display message box with a notice equal
        to text.

        Args:
            text (str): text to display

        Returns:
            int: system execution status.
        """
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(text)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        return retval

    def message_display_dict(self, content: dict):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        text = ''
        for key, value in content.items():
            text += f'{key}: {value}\n'
        msg.setText(text)
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        return retval


def main_GUI():
    """Initiate Qt application and GUI. Display the GUI and
    create plots.

    Returns:
        Tuple: QtApplication, GUI
    """
    app = QtWidgets.QApplication(sys.argv)
    init_values_file = os.path.join(os.getcwd(), 'lif.json')
    gui = Gui(init_values_file=init_values_file)
    # gui.show()
    # gui.create_plots()
    return app, gui


if __name__ == '__main__':
    app, gui = main_GUI()
    sys.exit(app.exec_())
