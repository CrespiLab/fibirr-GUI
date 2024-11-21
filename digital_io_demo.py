# -*- coding: utf-8 -*-
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import digital_io
from avaspec import *
import globals

class DigitalIoDialog(QDialog, digital_io.Ui_digital_io):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.DutyCycle1Edt.setText("{0:d}".format(50))
        self.DutyCycle2Edt.setText("{0:d}".format(50))
        self.DutyCycle3Edt.setText("{0:d}".format(50))
        self.DutyCycle5Edt.setText("{0:d}".format(50))
        self.DutyCycle6Edt.setText("{0:d}".format(50))
        self.DutyCycle7Edt.setText("{0:d}".format(50))
        self.Frequency123Edt.setText("{0:d}".format(1000))
        self.Frequency567Edt.setText("{0:d}".format(1000))
        self.DO1Chk.stateChanged.connect(self.on_DO1Chk_stateChanged)
        self.PWM1Chk.stateChanged.connect(self.on_DO1Chk_stateChanged)
        self.DO2Chk.stateChanged.connect(self.on_DO2Chk_stateChanged)
        self.PWM2Chk.stateChanged.connect(self.on_DO2Chk_stateChanged)
        self.DO3Chk.stateChanged.connect(self.on_DO3Chk_stateChanged)
        self.PWM3Chk.stateChanged.connect(self.on_DO3Chk_stateChanged)        
        self.DO4Chk.stateChanged.connect(self.on_DO4Chk_stateChanged) # has no PWM
        self.DO5Chk.stateChanged.connect(self.on_DO5Chk_stateChanged)
        self.PWM5Chk.stateChanged.connect(self.on_DO5Chk_stateChanged)
        self.DO6Chk.stateChanged.connect(self.on_DO6Chk_stateChanged)
        self.PWM6Chk.stateChanged.connect(self.on_DO6Chk_stateChanged)
        self.DO7Chk.stateChanged.connect(self.on_DO7Chk_stateChanged)
        self.PWM7Chk.stateChanged.connect(self.on_DO7Chk_stateChanged)        
        self.DO8Chk.stateChanged.connect(self.on_DO8Chk_stateChanged) # has no PWM
        self.DO9Chk.stateChanged.connect(self.on_DO9Chk_stateChanged) # has no PWM
        self.DO10Chk.stateChanged.connect(self.on_DO10Chk_stateChanged) # has no PWM

    @pyqtSlot()
    def on_GetDigitalInputsBtn_clicked(self):
        value1 = AVS_GetDigIn(globals.dev_handle, 0) # DI1
        self.DI1Chk.setChecked(value1 and 0x01)
        value2 = AVS_GetDigIn(globals.dev_handle, 1) # DI2
        self.DI2Chk.setChecked(value2 and 0x01)
        value3 = AVS_GetDigIn(globals.dev_handle, 2) # DI3
        self.DI3Chk.setChecked(value3 and 0x01)                
        return

    @pyqtSlot()
    def on_DO1Chk_stateChanged(self):
        if self.DO1Chk.isChecked():
            if self.PWM1Chk.isChecked():
                l_Perc = int(self.DutyCycle1Edt.text())
                l_Freq = int(self.Frequency123Edt.text())
                l_Res = AVS_SetPwmOut(globals.dev_handle, 0, l_Freq, l_Perc)
            else:
                l_Res = AVS_SetDigOut(globals.dev_handle, 0, 1) # DO1 on
        else:
            AVS_SetDigOut(globals.dev_handle, 0, 0) # DO1 off 
        return

    @pyqtSlot()
    def on_DO2Chk_stateChanged(self):
        if self.DO2Chk.isChecked():
            if self.PWM2Chk.isChecked():
                l_Perc = int(self.DutyCycle2Edt.text())
                l_Freq = int(self.Frequency123Edt.text())
                l_Res = AVS_SetPwmOut(globals.dev_handle, 1, l_Freq, l_Perc)
            else:
                l_Res = AVS_SetDigOut(globals.dev_handle, 1, 1) # DO2 on
        else:
            AVS_SetDigOut(globals.dev_handle, 1, 0) # DO2 off 
        return

    @pyqtSlot()
    def on_DO3Chk_stateChanged(self):
        if self.DO3Chk.isChecked():
            if self.PWM3Chk.isChecked():
                l_Perc = int(self.DutyCycle3Edt.text())
                l_Freq = int(self.Frequency123Edt.text())
                l_Res = AVS_SetPwmOut(globals.dev_handle, 2, l_Freq, l_Perc)
            else:
                l_Res = AVS_SetDigOut(globals.dev_handle, 2, 1) # DO3 on
        else:
            AVS_SetDigOut(globals.dev_handle, 2, 0) # DO3 off 
        return 

    @pyqtSlot()
    def on_DO4Chk_stateChanged(self):
        AVS_SetDigOut(globals.dev_handle, 3, self.DO4Chk.isChecked()) # DO4 on/off
        return 

    @pyqtSlot()
    def on_DO5Chk_stateChanged(self):
        if self.DO5Chk.isChecked():
            if self.PWM5Chk.isChecked():
                l_Perc = int(self.DutyCycle5Edt.text())
                l_Freq = int(self.Frequency567Edt.text())
                l_Res = AVS_SetPwmOut(globals.dev_handle, 4, l_Freq, l_Perc)
            else:
                l_Res = AVS_SetDigOut(globals.dev_handle, 4, 1) # DO5 on
        else:
            AVS_SetDigOut(globals.dev_handle, 4, 0) # DO5 off 
        return 

    @pyqtSlot()
    def on_DO6Chk_stateChanged(self):
        if self.DO6Chk.isChecked():
            if self.PWM6Chk.isChecked():
                l_Perc = int(self.DutyCycle6Edt.text())
                l_Freq = int(self.Frequency567Edt.text())
                l_Res = AVS_SetPwmOut(globals.dev_handle, 5, l_Freq, l_Perc)
            else:
                l_Res = AVS_SetDigOut(globals.dev_handle, 5, 1) # DO6 on
        else:
            AVS_SetDigOut(globals.dev_handle, 5, 0) # DO6 off 
        return

    @pyqtSlot()
    def on_DO7Chk_stateChanged(self):
        if self.DO7Chk.isChecked():
            if self.PWM7Chk.isChecked():
                l_Perc = int(self.DutyCycle7Edt.text())
                l_Freq = int(self.Frequency567Edt.text())
                l_Res = AVS_SetPwmOut(globals.dev_handle, 6, l_Freq, l_Perc)
            else:
                l_Res = AVS_SetDigOut(globals.dev_handle, 6, 1) # DO7 on
        else:
            AVS_SetDigOut(globals.dev_handle, 6, 0) # DO7 off 
        return                  

    @pyqtSlot()
    def on_DO8Chk_stateChanged(self):
        AVS_SetDigOut(globals.dev_handle, 7, self.DO8Chk.isChecked()) # DO8 on/off
        return

    @pyqtSlot()
    def on_DO9Chk_stateChanged(self):
        AVS_SetDigOut(globals.dev_handle, 8, self.DO9Chk.isChecked()) # DO9 on/off
        return

    @pyqtSlot()
    def on_DO10Chk_stateChanged(self):
        AVS_SetDigOut(globals.dev_handle, 9, self.DO10Chk.isChecked()) # DO10 on/off
        return   

