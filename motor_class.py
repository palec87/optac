#!/usr/bin/env python
"""
Interface to the stepper motors

1. First download Telemetrix4Arduino library via Arduino IDE
2. do Examples -> Telemetrix4Arduino -> Telemetrix4Arduino

Small motor which comes with Arduino starting kit (28BYJ-48) is
denoted as arduino_stepper
"""

import time
from telemetrix import telemetrix
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from optac.exceptions import NoMotorInitialized

__author__ = 'David Palecek'
__credits__ = ['Teresa M Correia', 'Rui Guerra']
__license__ = 'GPL'


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

        # checking regularly when the movement is over
        self.wait_const = wait_const

        # Can this be replaced by init_board()
        try:
            self.init_board()
        except NoMotorInitialized:
            raise

        self.init_motor()

    def init_board(self):
        try:
            self.board = telemetrix.Telemetrix()
        except RuntimeError:
            return

    def init_motor(self):
        if self.motor_type == 'Uno-stepper':
            self.motor = self.board.set_pin_mode_stepper(
                            interface=4,
                            pin1=8, pin2=10, pin3=9, pin4=11,
                        )
            self.set_max_speed(1000)
            self.full_rotation = 2048  # steps
            self.board.stepper_set_current_position(0, 0)
            self.turning = False
        else:
            raise ValueError('Unrecognised type of stepper motor')

        self.board.stepper_set_speed(self.motor, self.speed)
        self.board.stepper_set_acceleration(self.motor, self.acc)

    def set_max_speed(self, speed):
        """Set maximum speed of the given motor"""
        self.max_speed = speed
        try:
            self.board.stepper_set_max_speed(self.motor, self.max_speed)
        except NoMotorInitialized:
            print('Initialize a motor first.')

    def shutdown(self):
        """Shutdown board"""
        print('Motor shutting down.')
        return self.board.shutdown()

    def step_motor(self):
        """
        Only used for example script to move motor from the motor
        python CLI based on user integer input for relative stepping.
        Exit the script with 'exit' command.
        """
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

                print('motor moves by integer values or closes with "exit"')

            self.move_relative(dist)
            time.sleep(0.5)

    def move(self):
        """
        Move the stepper motor and keep cheking the
        for the running is over in the while loop.
        """
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

    ##############
    # PyQt slots #
    ##############
    start_rotate = pyqtSignal()
    rotation_rel_over = pyqtSignal(bool)

    @pyqtSlot()
    def move_relative(self, dist):
        """Move relative distance from current position

        Args:
            dist (int): Distance in steps
        """
        self.board.stepper_set_speed(self.motor, self.speed)
        self.board.stepper_move(self.motor, dist)

        self.move()

        self.rotation_rel_over.emit(not self.turning)
    _exit = pyqtSignal()

    rotation_abs_over = pyqtSignal(bool)

    @pyqtSlot()
    def move_absolute(self, position):
        """Move to absolute position relative to the position
        saved position 0, defined either at init or reset by user
        from the GUI

        Args:
            position (init): Position in steps (typically -2048:2048)
        """
        self.board.stepper_set_speed(self.motor, self.speed)
        self.board.stepper_move_to(self.motor, position)

        self.move()

        self.rotation_abs_over.emit(not self.turning)
    _exit = pyqtSignal()

    ############
    # Counters #
    ############
    def reset_move_counter(self):
        """Counting moves. Can be used for internal checking
        but currently not querried from the gui"""
        self.move_counter = 0

    def add_count(self):
        """add move count after move finished"""
        self.move_counter += 1

    def reset_absolute_zero(self):
        """Reset zero position which is used for absolute
        movements"""
        self.board.stepper_set_current_position(
                0,
                self.current_position_callback,
        )

    #############
    # Callbacks #
    #############
    def move_over_callback(self, data):
        # date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[2]))
        self.add_count()

    def current_position_callback(self, data):
        """Current position data in form of
        motor_id, current position in steps, time_stamp"""
        print(
            f'current_position_callback: \
            {data[0]}, {data[1]}, {data[2]}\n'
        )

    def is_running_callback(self, data):
        """Check if motor is running"""
        if data[1]:
            # print('The motor is running.')
            self.turning = True
        else:
            print('Motor IS STOPPED.')
            self.turning = False


def main():
    stepper = Stepper('28BYJ-48')
    stepper.step_motor()
    stepper.shutdown()


if __name__ == '__main__':
    main()
