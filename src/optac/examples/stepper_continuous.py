import sys
import time

from telemetrix import telemetrix

"""
Run a motor continuously without acceleration
"""

# Create a Telemetrix instance.
board = telemetrix.Telemetrix()


# for continuous motion, the callback is not used, but provided to meet the
# API needs.
def the_callback(data):
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[2]))
    print(f'Run motor {data[1]} completed motion at: {date}.')


# create an accelstepper instance for a TB6600 motor driver
# motor = board.set_pin_mode_stepper(interface=1, pin1=7, pin2=8)

# if you are using a 28BYJ-48 Stepper Motor with ULN2003
# comment out the line above and uncomment out the line below.
motor = board.set_pin_mode_stepper(interface=4, pin1=8, pin2=10, pin3=9, pin4=11)


# set the max speed and speed
board.stepper_set_max_speed(motor, 900)
board.stepper_set_speed(motor, 500)

# run the motor
board.stepper_run_speed(motor)
# board.stepper_run(motor)
# keep application running
while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        board.shutdown()
        sys.exit(0)
