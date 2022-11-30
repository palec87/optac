'''
author: David Palecek
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

Hardcoded path to the data saving folder
C:\\Users\\David Palecek\\Documents\\UAlg\\my_opt
'''

import sys
import os
from time import gmtime, strftime
import cv2
import json
import numpy as np
import time

from PyQt5 import QtCore, QtWidgets
from gui.optac_ui import Ui_MainWindow
import pyqtgraph as pg

from motor_class import Stepper
from camera_class import Sky_basic
from frame_processing import Frame
from radon_back_projection import Radon

from exceptions import NoMotorInitialized

# config #
#########
pg.setConfigOption('background', 'd')
pg.setConfigOption('foreground', 'k')


class Gui(QtWidgets.QMainWindow):
    def __init__(self, preloaded=False):
        super(Gui, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.show()

        # link GUI objects in optac_ui.py
        # and the methods from this class

        # motor control values
        self.ui.motor_speed.valueChanged.connect(self.update_motor_speed)
        self.ui.angle.valueChanged.connect(self.update_motor_angle)
        self.ui.motor_steps.valueChanged.connect(self.update_motor_steps)
        # motor buttons
        self.ui.rotate_motor_btn.clicked.connect(self.exec_rotate_motor_btn)
        self.ui.rotate_motor_btn.setDisabled(True)  # not implemented
        self.ui.step_motor_btn.clicked.connect(self.exec_step_motor_btn)
        self.ui.motor_init_btn.clicked.connect(self.exec_motor_init_btn)
        self.ui.motor_close_btn.clicked.connect(self.exec_motor_close_btn)
        self.ui.motor_close_btn.setDisabled(True)

        self.ui.motor_type_list.currentIndexChanged.connect(
            self.update_motor_type
            )
        self.ui.motor_type_list.addItem('Uno-stepper')

        # camera settings
        self.ui.frame_rate.valueChanged.connect(self.update_frame_rate)
        self.ui.camera_type_list.currentIndexChanged.connect(
            self.update_camera_type
            )
        self.ui.camera_type_list.addItem('Sky (1280x720)')

        self.ui.red_ch.toggled.connect(self.update_camera_channels)
        self.ui.green_ch.toggled.connect(self.update_camera_channels)
        self.ui.blue_ch.toggled.connect(self.update_camera_channels)
        self.ui.amp_ch.toggled.connect(self.update_camera_channels)

        # acquire settings
        self.ui.get_n_frames_btn.clicked.connect(self.exec_get_n_frames_btn)
        self.ui.n_frames.valueChanged.connect(self.update_n_frames)
        self.ui.frames2avg.valueChanged.connect(self.update_frames_to_avg)
        self.ui.accum_shots.toggled.connect(self.update_accum_shots)

        # measure panel
        # self.ui.expr_metadata.textChanged(self.update_metadata_expr)
        self.ui.run_opt_btn.clicked.connect(self.exec_run_opt_btn)
        self.ui.live_reconstruct.toggled.connect(self.update_live_recon_btn)
        self.ui.recon_px.valueChanged.connect(self.update_radon_idx)

        # Control panel
        self.ui.stop_btn.clicked.connect(self.exec_stop_btn)
        self.ui.exit_btn.clicked.connect(self.exec_exit_btn)
        self.ui.folder_btn.clicked.connect(self.select_folder)

        # plot control
        self.ui.toggle_hist.toggled.connect(self.update_toggle_hist)
        self.ui.min_hist.valueChanged.connect(self.update_hist_min)
        self.ui.max_hist.valueChanged.connect(self.update_hist_max)

        self.stop_request = False
        self.idle = True
        self.motor_on = False
        self.camera_on = False
        self.opt_running = False
        self.save_images = False
        self.live_recon = False
        self.accum_shots = False
        self.channel = 3
        self.frame_count = 0
        self.no_data_count = 0
        self.metadata = {}
        self.toggle_hist = False
        self.main_folder = os.getcwd()
        self.frame_count_set(self.frame_count)
        self.no_data_count_set(self.no_data_count)
        self.update_folder_path()
        self.ui.frame_rate.setDisabled(True)

        if preloaded is False:
            self.ui.motor_speed.setValue(500)
            self.ui.angle.setValue(400)
            self.ui.motor_steps.setValue(2)
            self.ui.frame_rate.setValue(24)
            self.ui.frames2avg.setValue(10)
            self.ui.n_frames.setValue(10)
            self.ui.accum_shots.setChecked(False)
            self.ui.amp_ch.setChecked(True)
            self.ui.live_reconstruct.setChecked(False)
            self.ui.recon_px.setValue(0)
            self.ui.min_hist.setValue(1)
            self.ui.max_hist.setValue(250)

            self.ui.camera_type_list.setCurrentIndex(0)
            self.ui.motor_type_list.setCurrentIndex(0)
            self.ui.rotate_motor_btn.setDisabled(True)

            # self.current_frame = Frame(np.array([0,1]), 0, 0)
            # self.current_frame.frame = np.zeros((1280,720))

    def update_hist_min(self):
        self.min_hist = self.ui.min_hist.value()

    def update_hist_max(self):
        self.max_hist = self.ui.max_hist.value()

    def update_toggle_hist(self):
        self.toggle_hist = self.ui.toggle_hist.isChecked()

    def update_folder_path(self):
        self.ui.folder_path.setText(self.main_folder)

    def update_radon_idx(self):
        self.radon_idx = self.ui.recon_px.value()

    def update_live_recon_btn(self):
        self.live_recon = self.ui.live_reconstruct.isChecked()

    def update_camera_channels(self, checked):
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

    def update_accum_shots(self):
        print(f'camera state, {self.camera_on}')
        self.accum_shots = self.ui.accum_shots.isChecked()
        if self.camera_on:
            print('updating accum prop')
            self.camera.accum = self.ui.accum_shots.isChecked()

    def update_motor_steps(self):
        self.motor_steps = self.ui.motor_steps.value()

    def update_n_frames(self):
        self.n_frames = self.ui.n_frames.value()

    def update_camera_type(self):
        self.camera_type = self.ui.camera_type_list.currentIndex()
        if self.camera_type == 0:
            self.resolution = (1280, 720)

    def update_motor_type(self):
        self.motor_type = self.ui.motor_type_list.currentIndex()
        if self.motor_type == 0:
            self.motor = 'Uno-stepper'
        else:
            raise ValueError

    def update_frame_rate(self):
        self.frame_rate = self.ui.frame_rate.value()

    def update_frames_to_avg(self):
        self.frames_to_avg = self.ui.frames2avg.value()

    def update_motor_speed(self):
        self.motor_speed = self.ui.motor_speed.value()
        if self.motor_on:
            self.stepper.speed = self.motor_speed

    def update_motor_angle(self):
        self.angle = self.ui.angle.value()

    def update_metadata_expr(self):
        self.metadata['exp_notes'] = self.ui.expr_metadata.toPlainText()

    ###################
    # execute buttons #
    ###################
    def exec_motor_init_btn(self):
        try:
            self.initialize_stepper()
        except NoMotorInitialized:
            self.append_history('No motor exception raised.')
        except Exception as e:
            self.append_history(f'Unknown motor problem, {e}.')
        else:
            self.motor_on = True
            self.ui.motor_init_btn.setDisabled(True)
            self.ui.motor_close_btn.setDisabled(False)

    def exec_get_n_frames_btn(self):
        self.append_history(
            f'Acq. {self.n_frames} frames, avg={self.frames_to_avg}'
                            )
        self.frame_count_set(0)
        self.no_data_count_set(0)

        # camera init
        if not self.camera_on:
            self.append_history('Initializing camera')
            self.camera = Sky_basic(
                            channel=1,
                            col_ch=self.channel,
                            resolution=self.resolution,
                            bin_factor=1
                            )
            self.camera_on = True
            self.acquire_thread = QtCore.QThread(parent=self)
            self.acquire_thread.start()
            self.camera.moveToThread(self.acquire_thread)
            self.camera.start_acquire.connect(self.camera.acquire)
            self.camera.data_ready.connect(self.post_acquire)
        self.acquire()

    def exec_run_opt_btn(self):
        self.create_saving_folder()
        self.disable_btns()
        self.save_images = True
        self.opt_running = True
        if not self.motor_on:
            self.initialize_stepper()
        self.ui.angle.setValue(
            int(self.stepper.full_rotation / self.motor_steps)
            )
        self.update_motor_angle()
        self.append_history(f'ANGLE: {self.angle}')
        self.unit_of_progress = 100/self.motor_steps
        self.step_counter = 0

        self.collect_metadata()
        self.metadata['exp_start'] = self.get_time_now()
        self.ui.progressBar.setValue(0)
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
        self.main_folder = str(QtWidgets.QFileDialog.getExistingDirectory(
                                self, "Select Directory"))
        self.append_history('new data folder selected')
        self.update_folder_path()

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
        self.metadata['exp_end'] = self.get_time_now()
        self.save_metadata()
        self.enable_btns()
        self.idling()

    def collect_metadata(self):
        self.metadata['motor_steps'] = self.motor_steps
        self.metadata['avg_per_frame'] = self.frames_to_avg
        self.metadata['images_per_step'] = self.n_frames

    def save_metadata(self):
        file_path = os.path.join(self.exp_path+'\\metadata.txt')
        with open(file_path, 'w') as f:
            f.write(json.dumps(self.metadata))

    def run_sweep(self):
        self.append_history(f'STEP {self.step_counter}')
        self.exec_get_n_frames_btn()

    def save_image(self):
        # time_stamp = self.get_time_now()
        fname = '_'.join([str(self.step_counter), str(self.frame_count)])
        if self.accum_shots:
            file_path = os.path.join(self.exp_path+'\\'+fname+'.txt')
            np.savetxt(file_path, self.current_frame.frame)
        else:
            file_path = os.path.join(self.exp_path+'\\'+fname+'.jpg')
            cv2.imwrite(file_path, self.current_frame.frame)

    ###############
    # Acquisition #
    ###############
    def acquire(self):
        '''acquire data from camera'''
        self.camera.average = self.frames_to_avg
        self.camera.start_acquire.emit()

    def post_acquire(self, frame, no_frame_count, minmax):
        try:
            self.current_frame.update_frame(frame, no_frame_count, minmax)
        except AttributeError:
            print('current_frame does not exist, creating a new one.')
            self.current_frame = Frame(frame, no_frame_count, minmax)

        self.current_frame_plot()
        if self.stop_request is True:
            self.finish()

        if self.save_images:
            self.save_image()

        self.frame_count_set(self.frame_count+1)

        if self.frame_count >= self.n_frames:
            if self.opt_running:
                self.post_step()
            else:
                self.idling()
        else:
            self.acquire()

        if self.stop_request is True:
            self.finish()

    def post_step(self):
        self.ui.progressBar.setValue(
                int((self.step_counter+1)*self.unit_of_progress))
        if self.live_recon:
            self.update_recon()
            self.current_recon_plot()

        if self.step_counter == self.motor_steps-1:
            self.post_sweep()
        else:
            self.step_counter += 1
            self.exec_step_motor_btn()
            self.run_sweep()

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
        try:
            self.current_recon.update_recon(
                self.current_frame.frame[:, self.radon_idx],
                self.step_counter)
        except AttributeError:
            print('current_recon does not exist, creating a new one.')
            self.current_recon = Radon(
                self.current_frame.frame[:, self.radon_idx],
                self.motor_steps)

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
            # this works
            self.ui.camera_live.setImage(self.current_frame.frame)
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
        return retval


def main():
    app = QtWidgets.QApplication(sys.argv)
    gui = Gui()
    gui.show()
    gui.create_plots()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
