# -*- coding: utf-8 -*-
"""
Based on: https://www.hackster.io/ansh2919/serial-communication-between-python-and-arduino-e7cce0
Modified by: Jorn Steen

Using the Adafruit MCP4725 breakout board for digital-to-analog (DAC) conversion

Operation:
- make sure that the correct script is uploaded to the Arduino
  (ArduinoCode_DAC_0to5V.ino)

GUI:
- Choose an LED -- the twelvebit_max gets adjusted from 4095 to the corrected 
  value according to the allowed maximum current of the LED

- IMPORTANT: The Current Limit on the LED Driver should be set to the max (1.2 A)
    
- Input a percentage using the slider
  -- this gets converted to a 12-bit string and then sent to the Arduino
"""

import serial ## for communication with Arduino COM port
import time

import tools.settings as Settings

########################################################

def write_read(arduino, x):
    if Settings.MODE_LED == "TEST":
        # print(f'==== TEST MODE ====\ntwelvebit_adjusted: {x}')
        print('==== TEST MODE ====')
    else:
        arduino.write(bytes(x, 'utf-8'))
        time.sleep(0.05)
        data = arduino.readline()
     	# print(f"data:{data}")
        return data

def turnLED_ON():
    # print(f"twelvebit_adjusted: {Settings.twelvebit_adjusted}")
    write_read(Settings.arduino, Settings.twelvebit_adjusted) ## send ON signal to Arduino (percentage-adjusted)
    Settings.LEDstatus = "ON"
    print(f"Turned {Settings.LEDstatus} the LED")
        
def turnLED_OFF():
    write_read(Settings.arduino, "0") ## send OFF signal to Arduino
    Settings.LEDstatus = "OFF"
    print(f"Turned {Settings.LEDstatus} the LED")

def SetToZero_twelvebitadjusted():
    Settings.twelvebit_adjusted = None
    print(f"=== Set twelvebit_adjusted to: {Settings.twelvebit_adjusted} ===")

########################################################
########################################################

def initialise_Arduino():
    """ Start COM port communication with Arduino (unless TEST MODE is on) """
    if Settings.MODE_LED == "TEST":
        pass
    else:
        # Settings.arduino = serial.Serial(port='COM4', baudrate=115200, timeout=.1) ## fibirr laptop
        Settings.arduino = serial.Serial(port='COM5', baudrate=115200, timeout=.1) ## other laptop
        time.sleep(2) ## need to wait a bit after opening the communication

def AdjustMaxCurrent(LED):
    MaxCurrent = Settings.MaxCurrents[LED]
    fraction = MaxCurrent / Settings.MaxCurrent_default
    twelvebit_max_thisLED = round(fraction * Settings.twelvebit_max_default)
    return MaxCurrent, twelvebit_max_thisLED

def percent_to_12bit(twelvebit_max, percent):
    fraction = percent / 100
    twelvebit_adj = twelvebit_max * fraction
    twelvebit_adj_round = round(twelvebit_adj)
    return twelvebit_adj_round
