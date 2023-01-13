#!/usr/bin/env python

'''
OPTac gui

Acquisition software for Optical Projection Tomography. If you are
interested in reconstruction and analysis, see

You can start cheap with the OPT with this GUI. 28BYJ-48 stepper motor and
Sky basics camera cost 2.44 and 40 bucks, respectively.

Control of the motors is done via Arduino board, notes on board
wiring can be found in the docs (TODO docs)

TODO ROI for the cameras which support that.
TODO Save images into a check radio button

Small motor which comes with Arduino starting kit (28BYJ-48) is
denoted as Uno-stepper
'''

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'

import sys
import os
from time import gmtime, strftime
import cv2
import json
import numpy as np

from PyQt5 import QtCore, QtWidgets
from gui.optac_ui import Ui_MainWindow
import pyqtgraph as pg

from motor_class import Stepper
from camera_class import Sky_basic, Virtual, Phonefix
from frame_processing import Frame
from radon_back_projection import Radon

from exceptions import NoMotorInitialized

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'

# config #
#########
pg.setConfigOption('background', 'd')
pg.setConfigOption('foreground', 'k')


class Gui(QtWidgets.QMainWindow):
    def __init__(self, init_values_file):
        super(Gui, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.show()

        self.init_file = init_values_file
        self.stop_request = False
        self.idle = True
        self.simul_mode = False
        self.motor_on = False
        self.camera_on = False
        self.opt_running = False
        self.save_images = False
        self.min_hist = None
        self.max_hist = None
        self.motor_steps = None
        self.channel = 3
        self.camera_port = None
        self.simul_angles = 128  # Number of rotation angles for Virtual camera
        self.frame_count = 0
        self.no_data_count = 0
        self.metadata = {}
        self.toggle_hist = False
        self.exp_path = None

        # link GUI objects in optac_ui.py
        # and the methods from this class

        # motor control values
        self.ui.motor_speed.valueChanged.connect(self._update_motor_speed)
        self.ui.angle.valueChanged.connect(self._update_motor_angle)
        self.ui.motor_steps.valueChanged.connect(self._update_motor_steps)
        # motor buttons
        self.ui.rotate_motor_btn.clicked.connect(self.exec_rotate_motor_btn)
        self.ui.rotate_motor_btn.setDisabled(True)  # not implemented
        self.ui.step_motor_btn.clicked.connect(self.exec_step_motor_btn)
        self.ui.motor_init_btn.clicked.connect(self.exec_motor_init_btn)
        self.ui.motor_close_btn.clicked.connect(self.exec_motor_close_btn)
        self.ui.motor_close_btn.setDisabled(True)

        self.ui.motor_type_list.currentIndexChanged.connect(
            self._update_motor_type
            )
        self.ui.motor_type_list.addItem('Uno-stepper')

        # camera settings
        self.ui.frame_rate.valueChanged.connect(self._update_frame_rate)
        self.ui.camera_type_list.currentIndexChanged.connect(
            self._update_camera_type
            )
        self.ui.camera_type_list.addItems(
            ['virtual', 'Sky (1280x720)', 'Phonefix'],
            )
        self.ui.camera_port.valueChanged.connect(self._update_camera_port)
        self.ui.flat_field_btn.clicked.connect(self.exec_flat_field_btn)

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
        # self.ui.expr_metadata.textChanged(self.update_metadata_expr)
        self.ui.run_opt_btn.clicked.connect(self.exec_run_opt_btn)
        self.ui.live_recon.toggled.connect(self._update_live_recon_btn)
        self.ui.radon_idx.valueChanged.connect(self._update_radon_idx)
        self.ui.n_sweeps.valueChanged.connect(self._update_n_sweeps)

        # Control panel
        self.ui.stop_btn.clicked.connect(self.exec_stop_btn)
        self.ui.exit_btn.clicked.connect(self.exec_exit_btn)
        self.ui.folder_btn.clicked.connect(self.select_folder)

        # plot control
        self.ui.toggle_hist.toggled.connect(self._update_toggle_hist)
        self.ui.min_hist.valueChanged.connect(self._update_hist_min)
        self.ui.max_hist.valueChanged.connect(self._update_hist_max)

        self.frame_count_set(self.frame_count)
        self.no_data_count_set(self.no_data_count)
        self.ui.amp_ch.setChecked(True)

        self.ui.frame_rate.setDisabled(True)
        self.ui.rotate_motor_btn.setDisabled(True)

        #  try loading last instance values
        try:
            f = open(init_values_file, 'r')
            init_values = json.loads(f.read())
            self._load_gui_values(init_values)
        except FileNotFoundError:
            self._no_init_values()

        self._recheck_values()

    def _recheck_values(self):
        self.motor_speed = self.ui.motor_speed.value()
        self.angle = self.ui.angle.value()
        self.motor_steps = self.ui.motor_steps.value()
        self.n_sweeps = self.ui.n_sweeps.value()
        self.frame_rate = self.ui.frame_rate.value()
        self.camera_port = self.ui.camera_port.value()
        self.frames_to_avg = self.ui.frames2avg.value()
        self.n_frames = self.ui.n_frames.value()
        self.accum_shots = self.ui.accum_shots.isChecked()
        self.live_recon = self.ui.live_recon.isChecked()
        self.radon_idx = self.ui.radon_idx.value()
        self.min_hist = self.ui.min_hist.value()
        self.max_hist = self.ui.max_hist.value()
        self.camera_type = self.ui.camera_type_list.currentIndex()
        self.motor_type = self.ui.motor_type_list.currentIndex()
        self.main_folder = self.ui.folder_path.toPlainText()

    def _load_gui_values(self, d):
        print('reading values')
        self.ui.motor_speed.setValue(d['motor_speed'])
        self.ui.angle.setValue(d['angle'])
        self.ui.motor_steps.setValue(d['motor_steps'])
        self.ui.n_sweeps.setValue(d['n_sweeps'])
        self.ui.frame_rate.setValue(d['frame_rate'])
        self.ui.camera_port.setValue(d['camera_port'])
        self.ui.frames2avg.setValue(d['frames_to_avg'])
        self.ui.n_frames.setValue(d['n_frames'])
        self.ui.accum_shots.setChecked(d['accum_shots'])
        self.ui.live_recon.setChecked(d['live_recon'])
        self.ui.radon_idx.setValue(d['radon_idx'])
        self.ui.min_hist.setValue(d['min_hist'])
        self.ui.max_hist.setValue(d['max_hist'])
        self.ui.camera_type_list.setCurrentIndex(d['camera_type_idx'])
        self.ui.motor_type_list.setCurrentIndex(d['motor_type_idx'])
        self.main_folder = d['folder_path']
        self._update_folder_path()

    def _save_gui_values(self):
        vals = {}
        vals['motor_speed'] = self.motor_speed
        vals['angle'] = self.angle
        vals['motor_steps'] = self.motor_steps
        vals['n_sweeps'] = self.n_sweeps
        vals['frame_rate'] = self.frame_rate
        vals['camera_port'] = self.camera_port
        vals['frames_to_avg'] = self.frames_to_avg
        vals['n_frames'] = self.n_frames
        vals['accum_shots'] = self.accum_shots
        vals['live_recon'] = self.live_recon
        vals['radon_idx'] = self.radon_idx
        vals['min_hist'] = self.min_hist
        vals['max_hist'] = self.max_hist
        vals['camera_type_idx'] = self.camera_type
        vals['motor_type_idx'] = self.motor_type
        vals['folder_path'] = self.main_folder
        with open(self.init_file, 'w') as f:
            f.write(json.dumps(vals))

    def _no_init_values(self):
        self.ui.motor_speed.setValue(500)
        self.ui.angle.setValue(400)
        self.ui.motor_steps.setValue(4)
        self.ui.n_sweeps.setValue(1)
        self.ui.frame_rate.setValue(24)
        self.ui.camera_port.setValue(1)
        self.ui.frames2avg.setValue(10)
        self.ui.n_frames.setValue(10)
        self.ui.accum_shots.setChecked(False)
        self.ui.live_recon.setChecked(False)
        self.ui.radon_idx.setValue(10)
        self.ui.min_hist.setValue(1)
        self.ui.max_hist.setValue(250)
        self.ui.camera_type_list.setCurrentIndex(0)
        self.ui.motor_type_list.setCurrentIndex(0)
        self.main_folder = os.getcwd()
        self._update_folder_path()

    def _update_camera_port(self):
        """Updates camera port form UI, TODO Does user need to know?.
        """
        self.camera_port = self.ui.camera_port.value()

    def _update_hist_min(self):
        """Set minimum level for main image histogram from UI
        """
        self.min_hist = self.ui.min_hist.value()
        self._check_hist_vals()

    def _update_hist_max(self):
        """Set maximum level for main image histogram from UI
        """
        self.max_hist = self.ui.max_hist.value()
        self._check_hist_vals()

    def _check_hist_vals(self):
        '''check if min hist is lower than hist max'''
        if self.max_hist is None or self.min_hist is None:
            return
        if self.ui.max_hist.value() <= self.ui.min_hist.value():
            self.message_hist_error()
            self.ui.max_hist.setValue(self.min_hist+1)

    def _update_toggle_hist(self):
        """Use histogram min/max levels if toggled"""
        self.toggle_hist = self.ui.toggle_hist.isChecked()

    def _update_folder_path(self):
        """Update saving folder path from UI"""
        self.ui.folder_path.setText(self.main_folder)

    def _update_radon_idx(self):
        """Which horizontal line of the main graph
        will be reconstructed, update input from UI.
        """
        self.radon_idx = self.ui.radon_idx.value()

    def _update_live_recon_btn(self):
        """If UI button checked, live reconstruction is active
        during the experiment.
        """
        self.live_recon = self.ui.live_recon.isChecked()

    def _update_camera_channels(self, checked):
        """Checks which camera channel is selected
        in the UI.

        Args:
            checked (bool): ischecked button
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
        return

    def _update_accum_shots(self):
        """If checked, shots are getting accumulated and not
        averaged. Effect is immediate if acquiring.
        """
        self.accum_shots = self.ui.accum_shots.isChecked()
        if self.camera_on:
            self.append_history(
                'Accumulate shots: '
                + str(self.ui.accum_shots.isChecked())
                )
            self.camera.accum = self.ui.accum_shots.isChecked()

    def _update_motor_steps(self):
        """Update number of motor steps per revolution from UI
        """
        self.motor_steps = self.ui.motor_steps.value()

    def _update_n_sweeps(self):
        """update number of sweeps, repetitions of the
        single OPT scan
        """
        self.n_sweeps = self.ui.n_sweeps.value()

    def _update_n_frames(self):
        """Update from UI how many frames to aquire
        Does not take into account averaging per frame.
        """
        self.n_frames = self.ui.n_frames.value()

    def _update_camera_type(self):
        """Update camera type from UI
        """
        self.camera_type = self.ui.camera_type_list.currentIndex()
        # self.initialize_camera()

    def _update_motor_type(self):
        """Update motor type from the UI"""
        self.motor_type = self.ui.motor_type_list.currentIndex()
        if self.motor_type == 0:
            self.motor = 'Uno-stepper'
        else:
            raise ValueError

    def _update_frame_rate(self):
        """Update frame rate from the UI
        """
        self.frame_rate = self.ui.frame_rate.value()

    def _update_frames_to_avg(self):
        """Number of frames to average per single image"""
        self.frames_to_avg = self.ui.frames2avg.value()

    def _update_motor_speed(self):
        """Update motor speed from the UI"""
        self.motor_speed = self.ui.motor_speed.value()
        if self.motor_on:
            self.stepper.speed = self.motor_speed

    def _update_motor_angle(self):
        """Update motor angle to turn in stepping mode
        For Uno-stepper, 2048 is a full turn"""
        self.angle = self.ui.angle.value()

    def _update_metadata_expr(self):
        """ update metadate from the UI text box"""
        self.metadata['exp_notes'] = self.ui.expr_metadata.toPlainText()

    ###################
    # execute buttons #
    ###################
    def exec_flat_field_btn(self):
        """integrate dark counts for 50x exposure time
        - flat field is rounded to int, for saving
        """
        # pop message to block the camera
        self.message_block()

        # camera init
        if not self.camera_on:
            self.initialize_camera()

        # acquire dataset
        self.acquire_flat_field()
        self.flat_field = self.current_frame.frame
        self.save_image('flat_field')

    def acquire_flat_field(self):
        self.camera.set_average(self.frames_to_avg * 50)
        # mes = self.message_flat_field_acq()
        self.camera.start_acquire.emit()
        # mes.close()

        self.append_history('')

    def linearity_calibration(self):
        """load calibration file, doing it alone is tedious,
        can be suggested to user
        """
        return

    def exec_motor_init_btn(self):
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

    def initialize_camera(self):
        self.append_history('Initializing camera')
        if self.camera_on:
            self.acquire_thread.quit()

        if self.camera_type == 0:
            # virtual
            self.initialize_virtual_camera()
            self.ui.motor_steps.setValue(self.simul_angles)
            self.ui.motor_steps.setDisabled(True)
        elif self.camera_type == 1:
            # Sky_basic
            self.resolution = (1280, 720)
            self.initialize_sky_basic()
            self.ui.motor_steps.setEnabled(True)
        elif self.camera_type == 2:
            # phonefix
            self.resolution = (1920, 1080)
            self.initialize_phonefix()
            self.ui.motor_steps.setEnabled(True)

        self.camera_on = True
        self.acquire_thread = QtCore.QThread(parent=self)
        self.acquire_thread.start()
        self.camera.moveToThread(self.acquire_thread)
        self.camera.start_acquire.connect(self.camera.acquire)
        self.camera.data_ready.connect(self.post_acquire)

    def initialize_sky_basic(self):
        self.simul_mode = False
        self.camera = Sky_basic(
                            channel=self.camera_port,
                            col_ch=self.channel,
                            resolution=self.resolution,
                            bin_factor=1
                            )

    def initialize_phonefix(self):
        self.simul_mode = False
        self.append_history('this camera can take longer to INIT')
        self.camera = Phonefix(
                            channel=self.camera_port,
                            col_ch=self.channel,
                            res=self.resolution,
                            )

    def initialize_virtual_camera(self):
        print('initializing virtual camera')
        self.simul_mode = True
        self.append_history(str(self.simul_mode))
        self.camera = Virtual(self.simul_angles)

    def exec_get_n_frames_btn(self):
        self.frame_count_set(0)
        self.no_data_count_set(0)

        # camera init
        if not self.camera_on:
            self.initialize_camera()

        self.acquire()

    def _check_motors(self):
        self.unit_of_progress = 100/self.motor_steps
        self.step_count = 0

        if self.simul_mode:
            return

        if not self.motor_on:
            self.initialize_stepper()

        self.ui.angle.setValue(
            int(self.stepper.full_rotation / self.motor_steps)
        )
        self.append_history(f'ANGLE: {self.angle}')

    def exec_run_opt_btn(self):
        self.create_saving_folder()
        self.disable_btns()
        self.save_images = True
        self.opt_running = True

        self._check_motors()

        self.collect_metadata()
        self.metadata['sweep_start'] = []
        self.metadata['sweep_finish'] = []
        self.metadata['sweep_start'].append(self.get_time_now())
        self.ui.progressBar.setValue(0)
        self.sweep_count_set(0)
        self.run_sweep()

    def exec_motor_close_btn(self):
        try:
            self.stepper.shutdown()
        except Exception as e:
            self.append_history(f'Problem closing motor, {e}')
        else:
            self.ui.motor_init_btn.setDisabled(False)
            self.ui.motor_close_btn.setDisabled(True)

    def exec_step_motor_btn(self):
        if self.simul_mode:
            self.append_history('simul mode, no rotation enabled')
            return
        self.append_history(f'motor speed: {self.stepper.speed}')
        self.stepper.move_relative(self.angle)

    def exec_rotate_motor_btn(self):
        '''
        continuous rotation
        - For this I need to fix the parallel threding
        to be able to acquire while rotating.
        '''
        pass

    def select_folder(self):
        folder = str(QtWidgets.QFileDialog.getExistingDirectory(
                                self, "Select Directory"))
        if not folder:
            self.append_history('no change in data folder')
            return

        self.main_folder = folder
        self._update_folder_path()
        self.append_history('new data folder selected')

    def exec_stop_btn(self):
        '''stops acquisition from running'''
        self.append_history('Stopped')
        self.stop_request = True
        try:
            self.camera.exit()
            self.acquire_thread.quit()
        except Exception as e:
            print(f'problem closing acquire thread: {e}')
        if self.motor_on:
            self.stepper.shutdown()
            self.motor_thread.quit()

    def exec_exit_btn(self):
        '''
        will exit from gui. some safeguarding
         in case exit is called before stop
         '''
        self.append_history('Stopped')

        if self.idle is False:
            self.finish()

        self._save_gui_values()
        self.close()

    #################
    # Initialize HW #
    #################
    def initialize_stepper(self):
        self.motor_thread = QtCore.QThread(parent=self)
        self.motor_thread.start()
        try:
            self.stepper = Stepper(self.motor)
        except NoMotorInitialized:
            self.append_history('No motor exception raised.')
            self.ui.motor_init_btn.setDisabled(False)
        except Exception as e:
            self.append_history(f'Unknown motor problem: {e}.')
            self.ui.motor_init_btn.setDisabled(False)
        self.stepper.moveToThread(self.motor_thread)

    def frame_count_set(self, count):
        '''update frame count in the current run'''
        self.frame_count = count
        self.ui.frame_count.display(self.frame_count)

    def no_data_count_set(self, count):
        '''update frame count in the current run'''
        self.no_data_count = count
        self.ui.no_data_count.display(self.no_data_count)

    def sweep_count_set(self, count):
        """update sweep count during OPT acquisition

        Args:
            count (int): sweep number
        """
        self.sweep_count = count
        self.ui.sweep_count.display(self.sweep_count)

    def disable_btns(self):
        self.ui.stepper_box.setDisabled(True)
        self.ui.camera_box.setDisabled(True)
        self.ui.acquire_settings_box.setDisabled(True)
        self.ui.measure_box.setDisabled(True)

    def enable_btns(self):
        self.ui.stepper_box.setDisabled(False)
        self.ui.camera_box.setDisabled(False)
        self.ui.acquire_settings_box.setDisabled(False)
        self.ui.measure_box.setDisabled(False)

    def post_sweep(self):
        """Register time of sweep finish.
        If last sweep, close experiment with post_opt()
        If not, run next sweep.
        """
        self.metadata['sweep_finish'].append(self.get_time_now())
        self.sweep_count_set(self.sweep_count + 1)
        if self.sweep_count == self.n_sweeps:
            self.post_opt()
        else:
            self.clear_sweep_data()
            self.run_sweep()

    def clear_sweep_data(self):
        self.current_frame = None
        self.step_count = 0

    def collect_metadata(self):
        self.metadata['n_steps'] = self.motor_steps
        self.metadata['n_sweeps'] = self.n_sweeps
        self.metadata['avg_per_frame'] = self.frames_to_avg
        self.metadata['images_per_step'] = self.n_frames

        if self.camera_type in [0, 1]:
            self.metadata['dynamic_range'] = np.int8
        self.metadata['user notes'] = self.ui.expr_metadata.toPlainText()

    def save_metadata(self):
        """Saving metadata dictionary in json format
        """
        file_path = os.path.join(self.exp_path, 'metadata.txt')
        with open(file_path, 'w') as f:
            f.write(json.dumps(self.metadata))

    def run_sweep(self):
        self.append_history(f'STEP {self.step_count}')
        self.exec_get_n_frames_btn()

    def save_image(self, fname=None):
        """Saving frames as images or text files in case accum shots
        is selected, which results in float numbers. Default file name
        is sweep_step_frame numbers separated by '_'.

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

        if self.accum_shots:
            file_path = os.path.join(self.exp_path, fname+'.txt')
            np.savetxt(file_path, self.current_frame.frame)
        else:
            file_path = os.path.join(self.exp_path, fname+'.jpg')
            cv2.imwrite(file_path, self.current_frame.frame)

    ###############
    # Acquisition #
    ###############
    def acquire(self):
        '''acquire data from camera'''
        self.camera.set_average(self.frames_to_avg)
        # only needed for the virtual camera
        if self.opt_running:
            self.camera.idx = self.step_count
        else:
            self.camera.idx = self.frame_count
        self.camera.start_acquire.emit()

    def post_acquire(self, frame, no_frame_count):
        try:
            self.current_frame.update_frame(frame, no_frame_count)
        except AttributeError:
            print('current_frame does not exist, creating a new one.')
            self.current_frame = Frame(frame, no_frame_count)

        self.current_frame_plot()

        # check is stop is requested
        if self.stop_request is True:
            self.finish()

        # saving
        if self.save_images:
            self.save_image()

        self.frame_count_set(self.frame_count+1)

        # checking for end of current step
        if self.frame_count >= self.n_frames:
            if self.opt_running:
                self.post_step()
            else:
                self.idling()
        else:
            self.acquire()

    def post_step(self):
        self.ui.progressBar.setValue(
                int((self.step_count+1)*self.unit_of_progress))
        if self.live_recon:
            self.update_recon()
            self.current_recon_plot()

        if self.step_count == self.motor_steps-1:
            self.post_sweep()
        else:
            self.step_count += 1
            self.exec_step_motor_btn()
            self.run_sweep()

    def post_opt(self):
        self.save_metadata()
        self.enable_btns()
        self.save_images = False
        self.opt_running = False
        self.clear_sweep_data()
        self.idling()

    ###############################
    # Metadata, saving, reporting #
    ###############################
    def get_date_now(self):
        return strftime("%y%m%d-%H-%M-%S", gmtime())

    def get_time_now(self):
        return strftime('%H-%M-%S +0000', gmtime())

    def create_saving_folder(self):
        self.exp_path = os.path.join(self.main_folder,
                                     self.get_date_now(),
                                     )
        os.mkdir(self.exp_path)
        self.append_history(f'created dir: {self.exp_path}')

    def append_history(self, message):
        self.ui.history.appendPlainText(message)

    ############
    # Plotting #
    ############
    def update_recon(self):
        # new version with catching exception
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

    def create_plots(self):
        '''defines defaults for each graph'''
        self.hist = self.ui.camera_live.getHistogramWidget()
        self.hist.fillHistogram(color=(255, 0, 0))

        self.ui.recon_live.plotItem.setLabels(
            left='pixel Y',
            bottom='pixel X'
        )

    def current_frame_plot(self):
        '''last frame plot in Align tab'''
        try:
            # this notworks
            # plot = pg.PlotItem()
            # plot.setLabel(axis='left', text='Y-axis')
            # plot.setLabel(axis='bottom', text='X-axis')
            # set the plot to ImageView's view
            # self.ui.camera_live = pg.ImageView(view=plot)

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

    def current_recon_plot(self):
        '''last frame plot in Align tab'''
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

    ###################
    # State functions #
    ###################
    def idling(self):
        self.idle = True
        # self.acquire_thread.terminate()
        # self.acquire_thread.quit()

    def finish(self):
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

    ############
    # Messages #
    ############
    def message_init_motor(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Initialize motor first")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        print(retval)
        return retval

    def message_hist_error(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("'Min hist' value has to be lower than 'Max hist'")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        print(retval)
        return retval

    def message_block(self):
        """before acquisition of the flat-field correction

        Returns:
            bool:
        """
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Block Camera")
        msg.setInformativeText("Just press once (be patient)")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        return retval

    def message_unblock(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("UnBlock Camera")
        msg.setInformativeText("Just press once.")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        retval = msg.exec_()
        return retval

    def message_flat_field_acq(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Acquiring Flat-Field")
        # retval = msg.exec_()
        return msg


def main_GUI():
    app = QtWidgets.QApplication(sys.argv)
    init_values_file = os.path.join(os.getcwd(), 'lif.json')
    gui = Gui(init_values_file=init_values_file)
    gui.show()
    gui.create_plots()
    return app, gui


if __name__ == '__main__':
    app, gui = main_GUI()
    sys.exit(app.exec_())
