# -*- coding: utf-8 -*-
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import analog_io
from avaspec import *
import globals

class AnalogIoDialog(QDialog, analog_io.Ui_analog_io):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.AO1Edt.setText("{0:.2f}".format(0.0))
        self.AO2Edt.setText("{0:.2f}".format(0.0))

    @pyqtSlot()
    def on_SetAnalogOutBtn_clicked(self):
        value1 = float(self.AO1Edt.text())
        value2 = float(self.AO2Edt.text())
        l_Ret = AVS_SetAnalogOut(globals.dev_handle, 0, value1)  # AO1
        if (0 != l_Ret):
            QMessageBox.critical(self, "Qt Demo", "AVS_SetAnalogOut failed on AO1, code {0:d}".format(l_Ret))
        l_Ret = AVS_SetAnalogOut(globals.dev_handle, 1, value2)  # AO2
        if (0 != l_Ret):
            QMessageBox.critical(self, "Qt Demo", "AVS_SetAnalogOut failed on AO2, code {0:d}".format(l_Ret))
        return

    @pyqtSlot()
    def on_GetAnalogInBtn_clicked(self):
        value1 = AVS_GetAnalogIn(globals.dev_handle, 5)  # AI1
        self.AI1Edt.setText("{0:.2f}".format(value1))
        value2 = AVS_GetAnalogIn(globals.dev_handle, 4)  # AI2
        self.AI2Edt.setText("{0:.2f}".format(value2))
        return 

    @pyqtSlot()
    def on_GetOnboardAIBtn_clicked(self):
        value1 = AVS_GetAnalogIn(globals.dev_handle, 0)  # onboard thermistor
        self.ThermistorX11Edt.setText("{0:.2f}".format(value1))
        value2 = AVS_GetAnalogIn(globals.dev_handle, 1)  # unused on AS7010
        self.E1V2Edt.setText("{0:.2f}".format(value2))
        value3 = AVS_GetAnalogIn(globals.dev_handle, 2)  # unused on AS7010
        self.E5VIOEdt.setText("{0:.2f}".format(value3))
        value4 = AVS_GetAnalogIn(globals.dev_handle, 3)  # unused on AS7010
        self.E5VUSBEdt.setText("{0:.2f}".format(value4))                       
        value5 = AVS_GetAnalogIn(globals.dev_handle, 6)  # digital temperature sensor
        self.NTC1X8Edt.setText("{0:.2f}".format(value5))
        value6 = AVS_GetAnalogIn(globals.dev_handle, 7)  # unused on AS7010
        self.NTC2X9Edt.setText("{0:.2f}".format(value6))          
        return                
