'''
author: David Palecek
Interface to the stepper motors

1. First download Telemetrix4Arduino library via Arduino IDE
2. do Examples -> Telemetrix4Arduino -> Telemetrix4Arduino
3. pip install telemetrix in your python environment

Small motor which comes with Arduino starting kit (28BYJ-48)
'''
import time
from telemetrix import telemetrix


class Error(Exception):
    """Base class for other exceptions"""
    pass


class NoMotorInitialized(Error):
    '''Raised when no motor found'''
    pass


class Stepper:
    def __init__(self, motor_type, speed=500, distance=100,
                 acc=400, wait_const=0.5):
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
        self.initialize_board()

    def initialize_board(self):
        self.board = telemetrix.Telemetrix()
        if self.motor_type == '28BYJ-48':
            self.motor = self.board.set_pin_mode_stepper(
                            interface=4,
                            pin1=8, pin2=10, pin3=9, pin4=11,
                        )
            self.set_max_speed(1000)
            self.turning = False
        else:
            raise ValueError('Unrecognised type of stepper motor')

        self.board.stepper_set_speed(self.motor, self.speed)
        self.board.stepper_set_acceleration(self.motor, self.acc)

    def set_max_speed(self, speed):
        self.max_speed = speed
        try:
            self.board.stepper_set_max_speed(self.motor, self.max_speed)
        except NoMotorInitialized:
            print('Initialize a motor first.')

    def set_speed(self, speed):
        self.speed = speed

    def set_distance(self, dist):
        self.distance = dist

    def shutdown(self):
        self.board.shutdown()

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

    def move_relative(self, dist):
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
