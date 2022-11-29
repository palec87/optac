'''
author: David Palecek
Interface to the stepper motors

1. First download Telemetrix4Arduino library via Arduino IDE
2. do Examples -> Telemetrix4Arduino -> Telemetrix4Arduino

Small motor which comes with Arduino starting kit (28BYJ-48) is
denoted as arduino_stepper
'''
import time
# import sys
from telemetrix import telemetrix
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from exceptions import NoMotorInitialized
# import numpy as np


class Stepper(QObject):
    def __init__(self, motor_type, speed=500, distance=100,
                 acc=200, wait_const=0.5):
        super(QObject, self).__init__()
        self.speed = speed
        self.max_speed = None
        self.dist = distance
        self.acc = acc
        self.move_counter = 0
        self.board = None
        self.motor_type = motor_type
        self.motor = None
        self.turning = None

        self.wait_const = wait_const  # checking when the movement is done
        try:
            self.initialize_board()
        except NoMotorInitialized:
            print('Motor init failed')

    def initialize_board(self):
        try:
            self.board = telemetrix.Telemetrix()
        except RuntimeError:
            pass
        if self.motor_type == 'Uno-stepper':
            self.motor = self.board.set_pin_mode_stepper(
                            interface=4,
                            pin1=8, pin2=10, pin3=9, pin4=11,
                        )
            self.set_max_speed(1000)
            self.full_rotation = 2048  # steps
            self.turning = False
        else:
            raise ValueError('Unrecognised type of stepper motor')

        self.board.stepper_set_speed(self.motor, self.speed)
        self.board.stepper_set_acceleration(self.motor, self.acc)
        print('everything ok')

    def set_max_speed(self, speed):
        self.max_speed = speed
        try:
            self.board.stepper_set_max_speed(self.motor, self.max_speed)
        except NoMotorInitialized:
            print('Initialize a motor first.')

    def shutdown(self):
        print('Motor shutting down.')
        return self.board.shutdown()

    def step_motor(self):
        run = True
        while run:
            command = input('Move by:')
            try:
                dist = int(command)
            except ValueError:
                if command == 'exit':
                    run = False
                    print('bye bye')
                    break
                else:
                    print('motor moves by integer values')

            self.move_relative(dist)
            time.sleep(0.5)

    start_rotate = pyqtSignal()
    rotation_over = pyqtSignal(bool)

    @pyqtSlot()
    def move_relative(self, dist):
        self.board.stepper_set_speed(self.motor, self.speed)
        print(self.speed, self.acc)
        self.board.stepper_move(self.motor, dist)
        # run the motor
        print('Starting motor...')
        self.turning = True
        self.board.stepper_run(
            self.motor,
            completion_callback=self.move_over_callback,
            )

        while self.turning:
            self.board.stepper_is_running(
                self.motor,
                callback=self.is_running_callback,
            )
            time.sleep(self.wait_const)
        time.sleep(self.wait_const)
        self.rotation_over.emit(not self.turning)
    _exit = pyqtSignal()

    def reset_move_counter(self):
        self.move_counter = 0

    def add_count(self):
        self.move_counter += 1

    #############
    # Callbacks #
    #############
    def move_over_callback(self, data):
        date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[2]))
        print(f'Motor {data[0]} motion completed: {date}.\n')
        self.add_count()

    # def shutdown_callback(self, data):
    #     print(f'Motor {data[0]} shutting down.')

    def current_position_callback(self, data):
        print(
            f'current_position_callback: \
            {data[0]}, {data[1]}, {data[2]}\n'
        )

    def is_running_callback(self, data):
        if data[1]:
            print('The motor is running.')
            self.turning = True
        else:
            print('The motor IS NOT running.')
            self.turning = False


def main():
    stepper = Stepper('28BYJ-48')
    stepper.step_motor()
    stepper.shutdown()


if __name__ == '__main__':
    main()
