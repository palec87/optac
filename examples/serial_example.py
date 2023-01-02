'''
author: David Palecek
Interface to serial Arduino interface
'''
import time
import sys
from telemetrix import telemetrix


# Convenience values for the pins.
# Note that the CS value is within a list
# These are the standard pins for many Arduino AVR boards.
# Change to match your particular board.

# if using an Uno, CS = 10, if Mkr WiFi 1010, CS = 9.
# change for your board.
CS = [10]
CS_PIN = 10

NUM_BYTES_TO_READ = 6

"""
 CALLBACKS

 These functions process the data returned from the MPU9250
"""


def the_device_callback(report):
    """
    Verify the device ID
    :param report: [SPI_REPORT, read register, Number of bytes, device_id]
    """
    if report[3] == 0x71:
        print('MPU9250 Device ID confirmed.')
    else:
        print(f'Unexpected device ID: {report[0]}, \
        {report[1]}, {report[2]}, {report[3]}')


# noinspection GrazieInspection
def accel_callback(report):
    """
    Print the AX, AY and AZ values.
    :param report: [SPI_REPORT, Register, Number of bytes, AX-msb, AX-lsb
    AY-msb, AY-lsb, AX-msb, AX-lsb]
    """
    print(f"AX = {int.from_bytes(report[3:5], byteorder='big', signed=True)}  "
          f"AY = {int.from_bytes(report[5:7], byteorder='big', signed=True)}  "
          f"AZ = {int.from_bytes(report[7:9], byteorder='big', signed=True)}  ")


def gyro_callback(report):
    # noinspection GrazieInspection
    """
        Print the GX, GY, and GZ values.
        :param report: [SPI_REPORT, Register, Number of bytes, GX-msb, GX-lsb
        GY-msb, GY-lsb, GX-msb, GX-lsb]
        """

    print(f"GX = {int.from_bytes(report[3:5], byteorder='big', signed=True)}  "
          f"GY = {int.from_bytes(report[5:7], byteorder='big', signed=True)}  "
          f"GZ = {int.from_bytes(report[7:9], byteorder='big', signed=True)}  ")


# This is a utility function to read SPI data
def read_data_from_device(board, register, number_of_bytes, callback):
    # noinspection GrazieInspection
    """
    This function reads the number of bytes using the register value.
    Data is returned via the specified callback.
    :param register: register value
    :param number_of_bytes: number of bytes to read
    :param callback: callback function
    """
    # the read bit is OR'ed in on the device sketch
    data = register

    # activate chip select
    board.spi_cs_control(CS_PIN, 0)

    board.spi_read_blocking(data, number_of_bytes, call_back=callback)

    # deactivate chip select
    board.spi_cs_control(CS_PIN, 1)
    time.sleep(.1)


def main():
    # Instantiate the TelemetrixRpiPico class accepting all default parameters.
    board = telemetrix.Telemetrix()

    # initialize the device
    board.set_pin_mode_spi(CS)

    # reset the device
    board.spi_cs_control(CS_PIN, 0)
    board.spi_write_blocking([0x6B, 0])
    board.spi_cs_control(CS_PIN, 1)

    time.sleep(.1)

    # get the device ID
    read_data_from_device(0x75, 1, the_device_callback)

    while True:
        try:
            time.sleep(1)
            # get the acceleration values
            read_data_from_device(board, 0x3b, 6, accel_callback)
            time.sleep(.1)

            # get the gyro values
            read_data_from_device(board, 0x43, 6, gyro_callback)
            time.sleep(.1)
        except KeyboardInterrupt:
            board.shutdown()
            sys.exit(0)


if __name__ == '__main__':
    main()
