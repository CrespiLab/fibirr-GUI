# -*- coding: utf-8 -*-
"""
Settings for LEDs
"""

###############################################################################
###############################################################################
###############################################################################

MaxCurrents = {
	'280 nm': 500,
	'310 nm': 600,
    '340 nm': 600,
	'365 nm': 1200,
    '395 nm': 1200,
    '455 nm': 1000,
    '505 nm': 1000,
    '530 nm': 1000,
    '625 nm': 1000,
    '780 nm': 800,
    'Max: 1200 mA': 1200
    }

twelvebit_zero = 0
twelvebit_max_default = 4095

MaxCurrent_default = 1200 ## mA

###############################################################################
###############################################################################
###############################################################################

twelvebit_max_thisLED = None
twelvebit_adjusted_int = 0
twelvebit_adjusted = ''

setLEDsettings = None

arduino = None

LEDstatus = "OFF"

count = 1

MODE_LED = ""
# MODE_LED = "TEST" ## use if no Arduino connected (test mode)

Default_AutoSaveFolder = r"user/back-up"

# Default_ArduinoCOMport = 'COM4' ## fibirr laptop
Default_ArduinoCOMport = 'COM5' ## other laptop