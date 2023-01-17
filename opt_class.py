#!/usr/bin/env python
"""
Classes which are a software backbone of the OPTac module and
OPT acquisition in general.

Other necessary classes are of course Camera and motor classes.
"""
import os
import cv2
import json
import numpy as np
import matplotlib.pyplot as plt
from time import gmtime, strftime

from .camera_class import Basic_usb, Dmk
from .motor_class import Stepper
from .exceptions import NoMotorInitialized
from .radon_back_projection import Radon

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


class Opt():
    """Class which should allow to acquire OPT from the script,
    command line, or even Jupyter notebook.
    """
    def __init__(self):
        # counters
        self.reset_counters()

        self.n_sweeps = None
        self.n_steps = None
        self.n_frames = None
        self.frames_to_avg = None
        self.accum_shots = None

        self.live_recon = False
        self.radon_idx = 100

        self.metadata = {}
        self.save_data = False
        self.main_folder = os.getcwd()
        self.exp_path = None

    def reset_counters(self):
        self.sweep_count = 0
        self.step_count = 0
        self.frame_count = 0

    def sweep_count_reset(self):
        self.sweep_count = 0

    def step_count_reset(self):
        self.step_count = 0

    def frame_count_reset(self):
        self.frame_count = 0

    def init_camera(self, type, port, channel, res):
        print('Initializing camera')
        if type in ['sky', 'phonefix']:
            self.camera = Basic_usb(port, channel, res)
        elif type == 'dmk':
            self.camera == Dmk()
        else:
            raise ValueError('Not recognised camera type')

    def get_camera_params(self):
        print(self.camera.__dict__)

    def get_frames(self, num, avg):
        self.frames_to_avg = avg
        self.n_frames = num

        img = None
        for _ in range(self.n_frames):
            self.current_frame = self.get_frame(self.frames_to_avg)
            self.plot_frame(img)

            if self.save_data:
                self.save_image()
            self.frame_count += 1

        if self.live_recon:
            try:
                self.plot_recon(img=None)
            except AttributeError as e:
                print(f'Proble plotting reconstruction: {e}')

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

        if self.accum_shots:
            file_path = os.path.join(self.exp_path, fname+'.txt')
            np.savetxt(file_path, self.current_frame)
        else:
            file_path = os.path.join(self.exp_path, fname+'.jpg')
            cv2.imwrite(file_path, self.current_frame)

    def get_frame(self, avg):
        self.camera.average = avg
        self.camera.acquire()
        return self.camera.data_avg

    def get_dark_field(self):
        """
        Actual dark-field acquisition

        1. Define camera.set_average to current * 50
        2. Call start_acquire
        """
        self.camera.set_average(self.frames_to_avg * 50)
        self.camera.acquire()
        print('Dark-field done')
        return self.camera.data_avg

    def set_main_folder(self, folder_path):
        self.main_folder = folder_path

    ###################
    # Motor functions #
    ###################
    def init_motor(self):
        try:
            self.initialize_stepper()
        except NoMotorInitialized:
            print('No motor found.')
        except Exception as e:
            print(f'Motor problem, {e}.')
        else:
            print('motor ready.')

    def initialize_stepper(self, type):
        """Initialize a stepper motor.

        1. Initialize or raise exception.
        """
        try:
            self.stepper = Stepper(type)
        except NoMotorInitialized:
            print('No motor exception raised.')
        except Exception as e:
            print(f'Unknown motor problem: {e}.')

    def step_motor(self, speed, angle):
        self.stepper.speed = speed
        self.angle = angle
        self.stepper.move_relative(self.angle)

    def set_live_recon(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError('input has to be boolean.')
        self.live_recon = value

    def set_recon_idx(self, value: int) -> None:
        self.recon_idx = value

    def run_opt(self, n_sweeps, n_steps, n_frames, n_averages):
        self.n_sweeps = n_sweeps
        self.n_steps = n_steps
        self.n_frames = n_frames
        self.n_averages = n_averages

        for sweep in range(self.n_sweeps):
            self.run_sweep()
            self.post_sweep(sweep)
            self.sweep_count += 1
        self.save_metadata()
        self.reset_counters()

    def run_sweep(self):
        for _ in range(self.n_steps):
            self.get_frames(self.n_frames, self.n_averages)
            if self.live_recon:
                self.reconstruct()
            self.step_count += 1
            self.step_motor()
        return

    def reconstruct(self):
        line = self.current_frame[self.radon_idx, :]
        if self.step_count == 0:
            self.recon = Radon(line, self.n_steps)
        else:
            self.recon.update_recon(self, line, self.step_count)

    def post_sweep(self):
        self.metadata['sweep_finish'].append(self.get_time_now())
        self.clear_sweep_data()

    def save_metadata(self):
        """
        Saving metadata dictionary in json format into the
        data saving folder.
        """
        file_path = os.path.join(self.exp_path, 'metadata.txt')
        with open(file_path, 'w') as f:
            f.write(json.dumps(self.metadata))

    def clear_sweep_data(self):
        if self.live_recon:
            self.recon = None

    ############
    # Plotting #
    ############
    def plot_frame(self, img):
        if img is None:
            img = plt.imshow(self.current_frame)
        else:
            img.set_data(self.current_frame)
        plt.title(f'counter: {self.frame_count+1}')
        plt.pause(0.2)
        plt.draw()

    def plot_recon(self, img):
        if img is None:
            img = plt.imshow(self.recon.output)
        else:
            img.set_data(self.recon.output)
        plt.title(f'Back projection: {self.step_count}/{self.n_steps}')
        plt.draw()
        return

    ##########
    # Saving #
    ##########
    def set_save_data(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError('input has to be boolean.')
        self.save_data = value

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
        print(f'created dir: {self.exp_path}')

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
        return strftime('%H-%M-%S +0000', gmtime())


class Plot():
    def __init__(self):
        pass

    def plot_frame(self, img, count):
        if img is None:
            img = plt.imshow(self.current_frame)
        else:
            img.set_data(self.current_frame)
        plt.title(f'counter: {count+1}')
        plt.pause(0.2)
        plt.draw()


class Data(Opt):
    """
    Class for processing chunks of frames comming from the camera
    Mostly averaging and software binning.

    Args:
        Opt (class): _description_
    """
    def __init__(self, frame, count):
        super(Data, self).__init__()
        self.frame = frame
        self.no_data_count = count

    def update_frame(self, frame, count):
        self.frame = frame
        self.no_data_count = count


class Recon():
    def __init__(self, n_steps, data):
        pass

    def save_data(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError('input has to be boolean.')
        self.save_data = value
