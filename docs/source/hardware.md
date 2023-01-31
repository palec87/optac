# Hardware

Items in each section ordered by performance. 

Even if you are a hobby builder with low price limits, OTPac offers support for *very* cheap combination of the hardware:

1. [Sky basics](https://www.amazon.com/Microscope-Skybasic-Magnification-Compatible-Smartphone/dp/B07DVFBVPF?th=1) camera for 40$.
2. Small stepper motor controlled via arduino for the total of less thatn 30$.

## Light sources

## Cameras
### [Sky basics](https://www.amazon.com/Microscope-Skybasic-Magnification-Compatible-Smartphone/dp/B07DVFBVPF?th=1)
*Setup*
Connect camera via the USB cable and you can right away capture the stream via e.g. OBS studio or in the case of OPTac via cv2 python module.

*Camera Features*
* USB simple setup, possible wi-fi too.
* 8 bit dynamic range.
* RGB chip, so you can separate channels.
* Bad objective, focusing out of the optical axis
* auto-exposure, so hard to correct and calibrate.

### [Phonefix](https://pt.aliexpress.com/item/32888369526.html?gatewayAdapt=glo2bra)
Note that the link above contains whlole setup, necessary is only camera and the C mount objective.

This camera has VGA/HDMI interface, which means it serves purely as an output device with intention to connect directly to a screen or other type of display. Your PC HDMI/VGA ports are also output connectors and cannot be used directly to receive/stream data from the phonefix camera.

Therefore, a [capture card](https://www.ign.com/articles/best-capture-card) for streming videos is necessary. Cheap option can be around 20$.

*Setup*
Connect VGA or HDMI camera output to the acquisition card and connect the card via USB to the PC. From this point, camera behaves basically the same as any other USB camera.

*Camera features*
* 1920x1080p, RGB chip
* 50/60 frame rate
* Objective good in comparison to the Sky basic camera.

### DMK
The Imagingsource cameras based on chips from sony (current CMOS workhorse). Different chips with diffrent specs are available in this so called industrial grade cameras. Typical price is few hundrets of $, imagingsource supposedly providing impecable support in terms of interfacing and designing custom applications.

*Setup*
Connect USB to the PC and you are good to go. This camera provides more control via the serial port.

*Settings*

*Camera features (DMK 37BUX252)*
* monochrome 12 bit dynamic range
* upto 120 frame rate
* 1/1.8 inch chip size
* 2048 x 1536 px
* Global shutter
* 3.45 um pixel size


### Other cameras
If you have similar camera with different specs, there is a widget where you can try to interface it with the current methods called:

TODO

## Stepper motors

## Arduino board
In order to start with the arduino board, you have to install 'Arduion IDE' for a start and testing. Follow the instructions based on your OS from Arduino IDE docs [here](https://docs.arduino.cc/software/ide-v1).


OPTac uses Telemetrix4Arduino library for Python, which you need to install onto your Arduino board via the IDE.

1. download Telemetrix4Arduino library via Arduino IDE:
    * Go to Tools -> Manage libraries -> and search telemetrix
    * Install
2. You can test its functionality in two ways:
    * There are several examples (after install) in Examples -> Telemetrix4Arduino -> Telemetrix4Arduino
    * Or if you have an OPTac source code, in the examples folder are scripts which enable you to play with the board using telemetrix package. The examples are mostly based on the documentation examples of the author of telemetrix Alan Yorinks and can be found [here](https://mryslab.github.io/telemetrix/). In particular, to control the stepper motor, telemetrix interfaces AccelStepper library by Mike McCauley.

## List of parts
For the sake of simplicity (not price, or performance), all parts are from Thorlabs.

1. Breadboard
2. LED holder


### Transmission mode

### Photoluminescence mode
In addition to the transmission mode, you need:
1. long pass filters needed to supress scattered excitation light.
2. filter holder + optomechanics.
3. Probably a box to block any ambient light.