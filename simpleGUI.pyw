"""
AvaSpec example script PyQt5_fulldemo.pyw modified by Jorn
Start: 2024-07-24

Goal: kinetic measurements with shutter control (closed between acquisitions)
- record Absorbance spectra (and auto-save them)
- also with LED Arduino control

IMPORTANT NOTES:
- I copied and renamed plot_mpl.py to plot.py, in order for the script to work with matplotlib
    (the original had plot_qwt.py as plot.py, for which a module named 'PyQt5.Qwt' is neeed)
- this file (PyQt5_fulldemo.pyw) contains the definitions and functions that are linked to the GUI objects
- the file "qtdemo.py" contains the code that builds the GUI: it was created from qtdemo.ui
    -- the function "connectSlotsByName" connects signals to slots according to a simple naming convention
        --- https://riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html#connecting-slots-by-name
        --- "Signal" to on_"Slot"_valueChanged (works apparently for _clicked as well)
        --- @pyqtSlot() is necessary to specify which of the possible overloaded Qt signals should be connected to the slot


TO DO/ADD:
[DONE] Shutter control: OPEN-MEASURE-CLOSE 
[] Shutter control over multiple measurements (user-input)
[] Add parameters: Interval (s); Number of Cycles; ...

[DONE] Add "Dynamic Dark Correction"
    => already done: measconfig.m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked() ## turns on Dynamic Dark Correction
    [DONE] Change name of feature in GUI to Dynamic Dark Correction

[] Add "Stray Light Suppression/Correction": 
    - [DONE] Ask Avantes: need the .py source code of the Qt_Demo_SLS compiled programme => does not exist...
    - [] Check the C++ code for inspiration and apply AVS_SuppressStrayLight in .py

[] "Record Reference" button that stores reference data (as np array) to be used here as well as saves it as a .csv file
[] "Record Dark" button that stores dark data and creates a dark-corrected Intensity spectrum by subtraction
[] Absorbance Mode: requires recording first a Reference Spectrum
[] Save spectra: Intensity and Absorbance separately
[] Add option to choose Reference data (from file) for current measurement
###
[] Measurement mode: Irradiation Kinetics
    - [] Need to add Arduino control for LED driver
[] Add MOD mode feature (pop-up window)
[] Measurement mode: Irr followed by non-Irr Kinetics (to measure irr and then thermal back-relaxation)
###
[] Trigger mode: External (Arduino-controlled)
###
([] Thorlabs powermeter (tlPM) code)
#######
Improve the spectral viewer:
[] add feature to remember certain previous spectra
[] add feature to plot value (Abs) at a user-defined wavelength vs spectrum/time
[] switch between Intensity and Absorbance modes (tabs)
#######
Improve code:
[] Remove * imports (convert to regular "full" imports)

"""
#!/usr/bin/env python3
# from ast import Str ## not used, but should be replaced by ast.Constant
import inspect
# import os
# import platform

import sys
import ctypes
import time

from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, QDateTime, Qt
from PyQt5.QtWidgets import (QMainWindow, QAbstractItemView, QTableWidgetItem, 
                             QMessageBox, QListWidget, qApp, QFileDialog, QApplication)

import avaspec as ava
import globals
import qtdemo
import analog_io_demo
import digital_io_demo
import eeprom_demo

##############################
######### ADDED BY ME ########
##############################
import numpy as np
import pandas as pd

#### DEMO MODE ###
# MODE = "DEMO"
MODE = "EXP"
##############################

##############################
########!!! TO DO ########
##############################

######## add to globals.py
portID_pin12_DO4 = 0
SHUTTER_OPEN = 1 ## value to open shutter
SHUTTER_CLOSE = 0 ## value to close shutter

    ## add to on_ActivateBtn_clicked
portID_pin12_DO4 = 3 ## portID of pin that controls the shutter
    ## re-name to PortID_InternalLightSource = 3
########

##############################
#############################

class QtdemoClass(QMainWindow, qtdemo.Ui_QtdemoClass):
    timer = QTimer() 
    SPECTR_LIST_COLUMN_COUNT = 5
    newdata = pyqtSignal(int, int) ## define new signal as a class attribute
        ## is used below in __init__
    dstrStatus = pyqtSignal(int, int)

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        #self.PreScanChk.hide()
        #self.SetNirSensitivityRgrp.hide()
        self.setStatusBar(self.statusBar)
        self.tabWidget.setCurrentWidget(self.CommunicationTab)
        self.SpectrometerList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.SpectrometerList.setColumnWidth(0,70)
        self.SpectrometerList.setColumnWidth(1,200)
        self.SpectrometerList.setColumnWidth(2,175)
        self.SpectrometerList.setColumnWidth(3,150)
        self.SpectrometerList.setColumnWidth(4,150)
        self.UpdateListBtn.setEnabled(False)
        self.ActivateBtn.setEnabled(False)
        self.DeactivateBtn.setEnabled(False)
        self.DigitalIoBtn.setEnabled(False)
        self.AnalogIoBtn.setEnabled(False)
        ###########################################
        self.ShowEepromBtn.setEnabled(False)
        self.ReadEepromBtn.setEnabled(False)
        self.WriteEepromBtn.setEnabled(False)
        ###########################################
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(False)
        self.ResetSpectrometerBtn.setEnabled(False)        
        self.ConnectUSBRBtn.setChecked(True)
        self.ConnectEthernetRBtn.setChecked(False)
        ###########################################
        self.SingleRBtn.setChecked(True)
        self.FixedNrRBtn.setChecked(False)
        # self.NrMeasEdt.setText("1") ## default 1 measurement
        self.ContinuousRBtn.setChecked(False)
        self.RepetitiveRBtn.setChecked(False)
        ###########################################
        # self.DstrStatusUpdateBtn.setEnabled(False)
        # self.DstrProgBar.setRange(0, 1)
        # self.DstrProgBar.setValue(0)
        # self.DssEvent_Chk.setChecked(False)
        # self.FoeEvent_Chk.setChecked(False)
        # self.IErrorEvent_Chk.setChecked(False)
        ###########################################
        self.SpectrometerList.clicked.connect(self.on_SpectrometerList_clicked)
#       self.OpenCommBtn.clicked.connect(self.on_OpenCommBtn_clicked)
    #       for buttons, do not use explicit connect together with the on_ notation, or you will get
    #       two signals instead of one!
        self.timer.timeout.connect(self.update_plot)
        self.timer.stop()
        
        ###########################################
        self.newdata.connect(self.handle_newdata) ## 
            ## this connects signal: pyqtSignal(int, int)
                ## to slot: self.handle_newdata
        ###########################################
        
        # self.dstrStatus.connect(self.handle_dstrstatus) ## Dynamics STR function
        self.DisableGraphChk.stateChanged.connect(self.on_DisableGraphChk_stateChanged)
        ava.AVS_Done()
    
    ###########################################
    ## address of the callback function that has to be defined in the user
    ## program, and will be called by the library
    ##!!! what are pparam1 and pparam2?
    def measure_cb(self, pparam1, pparam2):
        param1 = pparam1[0] # dereference the pointers
        param2 = pparam2[0]
        self.newdata.emit(param1, param2)
        ## this emits a signal from: pyqtSignal(int,int)
        ## is used in AVS_MeasureCallbackFunc (see below)
        ## so the signal is emitted only upon calling the callback function used in the MeasureButton functions
    ###########################################
    def dstr_cb(self, pparam1, pparam2):
        param1 = pparam1[0] # dereference the pointers
        temp = ctypes.cast(ctypes.addressof(pparam2), ctypes.POINTER(ctypes.c_uint)) # change to correct type
        param2 = temp[0]
        self.dstrStatus.emit(param1, param2)

    @pyqtSlot()
#   if you leave out the @pyqtSlot() line, you will also get an extra signal!
    #   so you might even get three!
    def on_OpenCommBtn_clicked(self):
        self.statusBar.showMessage('Open communication busy')
        la_Port = 0
        if (self.ConnectUSBRBtn.isChecked()):
            la_Port = 0
        if (self.ConnectEthernetRBtn.isChecked()): 
            la_Port = 256
        # if (self.ConnectBothRBtn.isChecked()):
        #     la_Port = -1      
        l_Ret = ava.AVS_Init(la_Port) ## Initializes the communication interface with the spectrometers (avaspec.py)
        if (l_Ret > 0):
            if (self.ConnectUSBRBtn.isChecked()):
                self.statusBar.showMessage("Initialized: USB (found devices: {0:d})".format(l_Ret))
            if (self.ConnectEthernetRBtn.isChecked()):
                self.statusBar.showMessage("Initialized: Ethernet (found devices: {0:d})".format(l_Ret))
            # if (self.ConnectBothRBtn.isChecked()):
            #     self.statusBar.showMessage("Initialized: Ethernet / USB (found devices: {0:d})".format(l_Ret))
            self.UpdateListBtn.setEnabled(True)
            self.on_UpdateListBtn_clicked()
        else:
            if (l_Ret == 0):
                self.statusBar.showMessage("No spectrometer found on network!")
            else:
                if (l_Ret == ava.ERR_ETHCONN_REUSE):
                    # A list of spectrometers can still be provided by the DLL
                    self.statusBar.showMessage("Server error; another instance is running!")
                    self.on_UpdateListBtn_clicked()
                else:
                    self.statusBar.showMessage("Server error; open communication failed with AVS_Init() error: {0:d}".format(l_Ret))
            ava.AVS_Done()
            # QMessageBox.critical(self,"Error","No devices were found!") 
        return

    @pyqtSlot()
    def on_CloseCommBtn_clicked(self):
        # First make sure that there is no measurement running, AVS_Done() must be called when 
        # there is no measurement running!
        if (globals.dev_handle != ava.INVALID_AVS_HANDLE_VALUE):
            ava.AVS_StopMeasure(globals.dev_handle)
            ava.AVS_Deactivate(globals.dev_handle) 
            globals.dev_handle = ava.INVALID_AVS_HANDLE_VALUE
        ava.AVS_Done()
        self.DisconnectGui()  
        self.statusBar.showMessage('')
        self.SpectrometerList.clearContents()
        self.SpectrometerList.setRowCount(0)
        return

    @pyqtSlot()
    def on_UpdateListBtn_clicked(self):
        l_RequiredSize = 0
        if (len(self.SpectrometerList.selectedItems()) != 0):
            self.currentItem = self.SpectrometerList.currentItem()
            globals.mSelectedDevRow = self.currentItem.row()
        else:
            globals.mSelectedDevRow = 0
        self.SpectrometerList.clearContents()
        if (self.ConnectUSBRBtn.isChecked()):
            lUsbDevListSize = ava.AVS_UpdateUSBDevices()
            l_pId = ava.AvsIdentityType * lUsbDevListSize
            l_pId = ava.AVS_GetList(lUsbDevListSize)
            self.SpectrometerList.setColumnCount(self.SPECTR_LIST_COLUMN_COUNT)
            self.SpectrometerList.setRowCount(lUsbDevListSize)
            x = 0
            while (x < lUsbDevListSize):
                self.SpectrometerList.setItem(x, 0, QTableWidgetItem(l_pId[x].SerialNumber.decode("utf-8")))
                if (l_pId[x].Status == b'\x00'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("UNKNOWN"))
                if (l_pId[x].Status == b'\x01' ):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("USB_AVAILABLE"))
                if (l_pId[x].Status == b'\x02'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("USB_IN_USE_BY_APPLICATION")) 
                if (l_pId[x].Status == b'\x03'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("USB_IN_USE_BY_OTHER"))                                     
                x += 1 

        if (self.ConnectEthernetRBtn.isChecked()):  
            l_pEth = ava.AVS_UpdateETHDevices(1)
            lEthListSize = len(l_pEth)
            l_pId = ava.AvsIdentityType * lEthListSize
            l_pId = ava.AVS_GetList(lEthListSize)
            self.SpectrometerList.setColumnCount(self.SPECTR_LIST_COLUMN_COUNT)
            self.SpectrometerList.setRowCount(lEthListSize)
            x = 0
            while (x < lEthListSize):
                self.SpectrometerList.setItem(x, 0, QTableWidgetItem(l_pId[x].SerialNumber.decode("utf-8")))
                if (l_pId[x].Status == b'\x04'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("ETH_AVAILABLE"))  
                if (l_pId[x].Status == b'\x05'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("ETH_IN_USE_BY_APPLICATION"))  
                if (l_pId[x].Status == b'\x06'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("ETH_IN_USE_BY_OTHER"))                                                  
                if (l_pId[x].Status == b'\x07'):
                    self.SpectrometerList.setItem(x, 1, QTableWidgetItem("ETH_ALREADY_IN_USE_USB"))
                PortNumItem = ("{0:d}").format(l_pEth[x].port)    
                self.SpectrometerList.setItem(x, 2, QTableWidgetItem(PortNumItem))
                LocalIpItem = ("{0:d}.{1:d}.{2:d}.{3:d}").format(l_pEth[x].LocalIp & 0xff,
                                                                (l_pEth[x].LocalIp >> 8) & 0xff,
                                                                (l_pEth[x].LocalIp >> 16) & 0xff,
                                                                (l_pEth[x].LocalIp >> 24))
                self.SpectrometerList.setItem(x, 3, QTableWidgetItem(LocalIpItem))
                RemoteHostIpItem =  ("{0:d}.{1:d}.{2:d}.{3:d}").format(l_pEth[x].RemoteHostIp & 0xff,
                                                                      (l_pEth[x].RemoteHostIp >> 8) & 0xff,
                                                                      (l_pEth[x].RemoteHostIp >> 16) & 0xff,
                                                                      (l_pEth[x].RemoteHostIp >> 24))
                self.SpectrometerList.setItem(x, 4, QTableWidgetItem(RemoteHostIpItem))    
                x += 1 

        return 

    @pyqtSlot()
    def on_ActivateBtn_clicked(self):
        if (len(self.SpectrometerList.selectedItems()) == 0): 
            QMessageBox.critical(self, "Qt Demo", "Please select the Serial Number of the device to activate")
        else:
            l_Id = ava.AvsIdentityType * 1
            l_Items = QListWidget()
            l_Items = self.SpectrometerList.selectedItems()
            l_Text = l_Items[0].text()
            l_Id.SerialNumber = l_Text.encode('utf-8')
            l_Id.UserFriendlyName = b"\x00"
            l_Id.Status = b"\x01"
            globals.dev_handle = ava.AVS_Activate(l_Id)
            if (ava.INVALID_AVS_HANDLE_VALUE == globals.dev_handle):
                QMessageBox.critical(self, "Qt Demo", "Error opening device {}".format(l_Text))
            else:
                m_Identity = l_Id
                globals.mSelectedDevRow = self.SpectrometerList.currentItem().row()
                self.on_UpdateListBtn_clicked()
                self.ConnectGui()
                # print(f"globals.wavelength: {globals.wavelength}")
                self.on_ReadEepromBtn_clicked() ## the ReadEepromBtn gets clicked: see def below
                    ## sets integration time and #averages to EEPROM default
                self.DefaultSettings() # set default settings
                dtype = 0
                dtype = ava.AVS_GetDeviceType(globals.dev_handle)  
                if (dtype == 0):
                    self.DeviceTypeEdt.setText("Unknown")
                if (dtype == 1):
                    self.DeviceTypeEdt.setText("AS5216")
                if (dtype == 2):
                    self.DeviceTypeEdt.setText("ASMini")                                        
                if (dtype == 3):
                    self.DeviceTypeEdt.setText("AS7010")
                if (dtype == 4):
                    self.DeviceTypeEdt.setText("AS7007")                    
                # self.DstrRBtn.setEnabled(dtype == 3)  # only available on AS7010
                ######
                ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
        return

###############################################################################
###############################################################################
###############################################################################
    def print_vars(self, *args):
        for v in args:
            # Find all attribute names on self that reference this value
            names = [name for name, val in self.__dict__.items() if val is v]
            if names:
                print(f"{names[0]} = {v}")
            else:
                print(f"<unknown> = {v}")

    def print_settings(self):
        self.print_vars(self.measconfig.m_StartPixel, self.measconfig.m_StopPixel,
                        self.measconfig.m_IntegrationTime, self.measconfig.m_IntegrationDelay,
                        self.measconfig.m_NrAverages, 
                        self.measconfig.m_CorDynDark_m_Enable, self.measconfig.m_CorDynDark_m_ForgetPercentage,
                        self.measconfig.m_SaturationDetection,
                        self.measconfig.m_Trigger_m_Mode)

    @pyqtSlot()
    def on_SettingsBtn_clicked(self):
        print("on_SettingsBtn_clicked")
        self.measconfig.m_StartPixel = int(self.StartPixelEdt.text())
        self.measconfig.m_StopPixel = int(self.StopPixelEdt.text())
        self.measconfig.m_IntegrationTime = float(self.IntTimeEdt.text())
        l_NanoSec =  float(self.IntDelayEdt.text())
        self.measconfig.m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0)
        self.measconfig.m_NrAverages = int(self.AvgEdt.text())
        ####
        self.measconfig.m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked() ## turns on Dynamic Dark Correction
        self.measconfig.m_CorDynDark_m_ForgetPercentage = int(self.DarkCorrPercEdt.text()) ## sets percentage (100% is recommended)
        ####
        self.measconfig.m_SaturationDetection = int(self.SatDetEdt.text())
        ###########################################
        if (self.InternalTriggerBtn.isChecked()):
            self.measconfig.m_Trigger_m_Mode = 0
            ##!!! DEFINE m_Trigger_m_Mode = 0 : internal shutter of light source (change name?)
        if (self.ExternalTriggerBtn.isChecked()):
            self.measconfig.m_Trigger_m_Mode = 1
            ##!!! DEFINE m_Trigger_m_Mode = 1 : external Arduino-controlled shutter (change name?)

        self.print_settings()

    @pyqtSlot()
    def on_DarkMeasBtn_clicked(self):
        print("on_DarkMeasBtn_clicked")
        self.print_settings()
        globals.MeasurementType = "Dark"
        if MODE == "DEMO":
            print("DEMO MODE: on_DarkMeasBtn_clicked clicked")
        elif MODE == "EXP":
            ret = ava.AVS_UseHighResAdc(globals.dev_handle, True)
            ret = ava.AVS_EnableLogging(False)
            ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)
            if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_TCD1304):
                ava.AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked())
            if ((globals.DeviceData.m_Detector_m_SensorType == ava.SENS_HAMS9201) or 
                (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU256LSB) or
                (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU512LDB)):
                ava.AVS_SetSensitivityMode(globals.dev_handle, self.HighSensitivityRBtn.isChecked())
            ###########################################
            l_NrOfScans = int(1) # 1 scan
            ###########################################
            if (self.DarkMeasBtn.isEnabled()):
                print ("on_DarkMeasBtn_clicked === DarkMeasBtn enabled")
                globals.m_DateTime_start = QDateTime.currentDateTime()
                globals.m_SummatedTimeStamps = 0.0
                globals.m_Measurements = 0
                globals.m_Failures = 0
                self.TimeSinceStartEdt.setText("{0:d}".format(0))
                self.NrScansEdt.setText("{0:d}".format(0))
                self.NrFailuresEdt.setText("{0:d}".format(0))
            # self.DarkMeasBtn.setEnabled(False) 
            self.timer.start(200)   
            ###########################################
            avs_cb = ava.AVS_MeasureCallbackFunc(self.measure_cb) # (defined above)
            l_Res = ava.AVS_MeasureCallback(globals.dev_handle, avs_cb, l_NrOfScans)
             ## l_NrOfScans is number of measurements to do. -1 is infinite, -2 is used to
             ## l_Res returns (=) 0 if the measurement callback is successfully started
            if (0 != l_Res): ## if not zero, measurement callback was not started, so it is a fail
                 self.statusBar.showMessage("AVS_MeasureCallback failed, error: {0:d}".format(l_Res))    
            else:
                ####!!! TEST THIS: ####
                # ##### CLOSE SHUTTER ##### just to be sure
                ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
                time.sleep(0.5) ## short delay between Close Shutter and Measure
                qApp.processEvents() ## 
                self.statusBar.showMessage("Dark Spectrum recorded")
                print(f"on_DarkMeasBtn_clicked === globals.m_Measurements: {globals.m_Measurements}") 
                 
            return

##!!! ADD provision that Dark Measurement needs to have been carried out
    @pyqtSlot()
    def on_RefMeasBtn_clicked(self):
        print("on_RefMeasBtn_clicked")
        self.print_settings()
        globals.MeasurementType = "Ref"
        if MODE == "DEMO":
            print("DEMO MODE: on_RefMeasBtn_clicked clicked")
        elif MODE == "EXP":
            ret = ava.AVS_UseHighResAdc(globals.dev_handle, True)
            ret = ava.AVS_EnableLogging(False)
            ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)
            if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_TCD1304):
                ava.AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked())
            if ((globals.DeviceData.m_Detector_m_SensorType == ava.SENS_HAMS9201) or 
                (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU256LSB) or
                (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU512LDB)):
                ava.AVS_SetSensitivityMode(globals.dev_handle, self.HighSensitivityRBtn.isChecked())
            ###########################################
            l_NrOfScans = int(1) # 1 scan
            
            ###########################################
            #### changed to DarkMeasBtn ####
            if (self.RefMeasBtn.isEnabled()):
                print ("on_RefMeasBtn_clicked === RefMeasBtn enabled")
                globals.m_DateTime_start = QDateTime.currentDateTime()
                globals.m_SummatedTimeStamps = 0.0
                globals.m_Measurements = 0
                globals.m_Failures = 0
                self.TimeSinceStartEdt.setText("{0:d}".format(0))
                self.NrScansEdt.setText("{0:d}".format(0))
                self.NrFailuresEdt.setText("{0:d}".format(0))
            # self.RefMeasBtn.setEnabled(False) 
            self.timer.start(200)   
            ###########################################
            avs_cb = ava.AVS_MeasureCallbackFunc(self.measure_cb) # (defined above)
            l_Res = ava.AVS_MeasureCallback(globals.dev_handle, avs_cb, l_NrOfScans)
             ## l_NrOfScans is number of measurements to do. -1 is infinite, -2 is used to
             ## l_Res returns (=) 0 if the measurement callback is successfully started
            if (0 != l_Res): ## if not zero, measurement callback was not started, so it is a fail
                 self.statusBar.showMessage("AVS_MeasureCallback failed, error: {0:d}".format(l_Res))    
            else:
                ####!!! TEST THIS: ####
                ## OPEN SHUTTER ###
                ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_OPEN) ## open shutter
                time.sleep(0.5) ## short delay between Open Shutter and Measure
                qApp.processEvents()
                self.statusBar.showMessage("Reference Spectrum recorded")
                print(f"on_RefMeasBtn_clicked === globals.m_Measurements: {globals.m_Measurements}") 
                ## CLOSE SHUTTER ###
                time.sleep(0.1) ## short delay between Measure and Close Shutter
                ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
                #######
                self.StartMeasBtn.setEnabled(True) ## enable Start Measurement button
                ##!!! NEED TO ADD CHECKS

            return

###!!! in case of Absorbance Mode: add an if-check for the Ref having been measured
    ## self.AbsorbanceMode.isChecked()
    @pyqtSlot()
    def on_StartMeasBtn_clicked(self):
        globals.MeasurementType = "Measurement"
        if MODE == "DEMO":
            print("DEMO MODE: on_StartMeasBtn_clicked clicked")
        elif MODE == "EXP":
            ####!!! ADD Save As window here
            # globals.filename = QFileDialog.getSaveFileName(self, 'Select filename',
            #                                                'c:\\Users\\SyrrisAsia\\Desktop\\test',
            #                                                "Comma-separated values (.csv)")
            # print(f"PRINTED globals.filename[0]: {globals.filename[0]}")
            ################################################################
            ret = ava.AVS_UseHighResAdc(globals.dev_handle, True)
            ret = ava.AVS_EnableLogging(False)
            ###########################################
            ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)
            if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_TCD1304):
                ava.AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked())
            if ((globals.DeviceData.m_Detector_m_SensorType == ava.SENS_HAMS9201) or 
                (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU256LSB) or
                (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU512LDB)):
                ava.AVS_SetSensitivityMode(globals.dev_handle, self.HighSensitivityRBtn.isChecked())
            ###########################################
            if (self.SingleRBtn.isChecked()): ## added
                l_NrOfScans = int(1)
                ##!!! need to test (and add shutter code)
            if (self.FixedNrRBtn.isChecked()):
                l_NrOfScans = int(self.NrMeasEdt.text())
                ## default of FixedNr is 1 (see above) so it is a Single Measurement
            if (self.ContinuousRBtn.isChecked()):
                l_NrOfScans = -1
            if (self.RepetitiveRBtn.isChecked()):
                 l_NrOfScans = int(self.NrMeasEdt.text())
            ###########################################
            if (self.StartMeasBtn.isEnabled()):
                globals.m_DateTime_start = QDateTime.currentDateTime()
                globals.m_SummatedTimeStamps = 0.0
                globals.m_Measurements = 0
                globals.m_Failures = 0
                self.TimeSinceStartEdt.setText("{0:d}".format(0))
                self.NrScansEdt.setText("{0:d}".format(0))
                self.NrFailuresEdt.setText("{0:d}".format(0))
            self.StartMeasBtn.setEnabled(False) 
            self.StopMeasBtn.setEnabled(True)
            self.timer.start(200)   
            ###########################################
            ###!!! add an if-check for the Ref having been measured
            ##!!! what is the difference between Repetitive and Fixed Number?
            if (self.RepetitiveRBtn.isChecked()):
            # if (self.RepetitiveRBtn.isChecked()):
                ##!!! I think this function is incomplete, because it does not contain l_NrOfScans??
                lmeas = 0
                while (self.StartMeasBtn.isEnabled() == False):
                    avs_cb = ava.AVS_MeasureCallbackFunc(self.measure_cb)
                    l_Res = ava.AVS_MeasureCallback(globals.dev_handle, avs_cb, 1)
                    while (globals.m_Measurements - lmeas) < 1: ##!!! what is globals.m_Measurements: the number of measurements made?
                                                            ## yes: it gets counted at handle_newdata
                                                            ## but when does that get called?
                        time.sleep(0.001)
                        qApp.processEvents()
                    lmeas += 1
                    ##!!! add shutter OPEN-CLOSE code here??
            ###########################################
            else:    
                avs_cb = ava.AVS_MeasureCallbackFunc(self.measure_cb) # (defined above)
                l_Res = ava.AVS_MeasureCallback(globals.dev_handle, avs_cb, l_NrOfScans)
                ## l_NrOfScans is number of measurements to do. -1 is infinite, -2 is used to
                    ## it is defined above and depends on which Measurement Mode option is checked
                ## l_Res returns (=) 0 if the measurement callback is successfully started
                if (0 != l_Res): ## if not zero, measurement callback was not started, so it is a fail
                    self.statusBar.showMessage("AVS_MeasureCallback failed, error: {0:d}".format(l_Res))    
                else:
                    ###########################################
                    ####!!! TEST THIS: ####
                    if (self.SingleRBtn.isChecked()):
                        #######
                        ##!!! CHECK digital_io_demo.py for SetDigOut shenanigans
                        ## OPEN SHUTTER ###
                        ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_OPEN) ## open shutter
                        time.sleep(0.5) ## short delay between Open Shutter and Measure
                        qApp.processEvents()
                    
                        ##### CLOSE SHUTTER #####
                        time.sleep(0.5) ## short delay between Measure and Close Shutter
                        ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
                        #######
                
                    elif (self.FixedNrRBtn.isChecked()):
                        ## either make this the Kinetic or make the Repetitive the Kinetic
                        ##!!! TRY AVS_Measure (maybe not necessary anymore)


                        for i in range(l_NrOfScans):
		
                        ### OPEN SHUTTER ###
                            ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_OPEN) ## open shutter
                            time.sleep(0.5) ## short delay between Open Shutter and Measure
                        
                        ######## MY WAY ########
                            qApp.processEvents() ## qApp is from PyQt5
                        ##############################
                                
                        # ########## AVASPEC WAY ##########
                            # while globals.m_Measurements <= l_NrOfScans:
                            #     time.sleep(0.001)
                            #     qApp.processEvents() ## qApp is from PyQt5
                        ##############################

                        #######################
                        # ##### CLOSE SHUTTER #####
                            time.sleep(0.5) ## short delay between Open Shutter and Measure
                            ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
                            time.sleep(0.5) ## delay between Close Shutter and Open Shutter

                #######
                    else:        
                        if self.ContinuousRBtn.isChecked():
                            while True: 
                                time.sleep(0.001)
                                qApp.processEvents()
                                ##!!! HERE does this somehow re-activate the StartMeasBtn?
                                ## and does it prevent the GUI from exiting correctly?

            self.StartMeasBtn.setEnabled(True) 
            self.StopMeasBtn.setEnabled(False)
            return

    @pyqtSlot()
    def on_StopMeasBtn_clicked(self): 
        ret = ava.AVS_StopMeasure(globals.dev_handle)
        self.StartMeasBtn.setEnabled(True)
        self.timer.stop()
        return

    @pyqtSlot()
    def update_plot(self):
        if (self.DisableGraphChk.isChecked() == False):
            self.plot.update_plot() ## plot.py/update_plot() uses the new data: globals.spectraldata
        if (globals.m_Measurements == int(self.NrMeasEdt.text())):
            self.StartMeasBtn.setEnabled(True)    
        return         

    @pyqtSlot()
    def auto_save(self, filename, mode, spectrum):
        '''
        Saves spectrum as .csv file
        ##!!! CAN BE SIMPLIFIED

        Parameters
        ----------
        filename : string
            DESCRIPTION.
        mode : string
            DESCRIPTION.
        spectrum : list
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
        FileObject = filename+f"_{mode}_"+".csv"
        data_vstack = np.vstack((globals.wavelength,
                                     spectrum))
        data_transposed = np.transpose(data_vstack)
        xydata = pd.DataFrame(data_transposed,columns=["Wavelength (nm)","Pixel values"])
        xydata.to_csv(FileObject,index=False)
        print(f"{mode} spectrum auto-saved as {FileObject}")

    @pyqtSlot(int, int)
    def handle_newdata(self, ldev_handle, lerror):
        '''
        Order of actions for spectra with Dark and SLS correction
        1) record and save Dark
        2) record Scope spectrum
        3) substract Dark from Scope (Scope_DarkCorrected = Scope - Dark)
        4) obtain the SLS-corrected spectrum (Scope_DarkSLSCorrected) using AVS_SuppressStrayLight 
           from the dark-corrected spectrum (Scope_DarkCorrected)
           
       ##!!! CHANGE TO USING NUMPY ARRAYS
        '''
        if (lerror >= 0):
            if ((ldev_handle == globals.dev_handle) and (globals.pixels > 0)):
                if (lerror == 0): # normal measurements
                    self.statusBar.showMessage("Meas.Status: success")
                    timestamp = 0
                    globals.m_Measurements += 1 ## counter for number of measurements
                    timestamp, globals.spectraldata = ava.AVS_GetScopeData(globals.dev_handle) ## globals.spectraldata is 4096 element array of doubles
                    globals.wavelength = globals.wavelength_doublearray[:globals.pixels]
                    ##!!! DON'T NEED _doublearray VARIABLES, I THINK
                    ##################
                    filename = globals.filename
                    # print(f"handle_newdata === filename: {filename}")
                    ##################
                    if globals.MeasurementType == "Dark":
                        globals.DarkSpectrum_doublearray = globals.spectraldata
                        globals.DarkSpectrum = globals.DarkSpectrum_doublearray[:globals.pixels]
                        ####
                        self.auto_save(filename, "Dark", globals.DarkSpectrum)
                        self.statusBar.showMessage("Dark Spectrum auto-saved") ## Message box added
                    elif globals.MeasurementType == "Ref":
                        globals.RefSpectrum_doublearray = globals.spectraldata
                        print(f"globals.RefSpectrum_doublearray type: {type(globals.RefSpectrum_doublearray)}")
                        globals.RefSpectrum = globals.RefSpectrum_doublearray[:globals.pixels]
                        print(f"globals.RefSpectrum type: {type(globals.RefSpectrum)}")
                        self.auto_save(filename, "Ref", globals.RefSpectrum)
                        #### Dark-Corrected ####
                        globals.RefSpectrum_DarkCorr = [globals.RefSpectrum_doublearray[x] - globals.DarkSpectrum_doublearray[x] for x in range(globals.pixels)]
                        print(f"globals.RefSpectrum_DarkCorr type: {type(globals.RefSpectrum_DarkCorr)}")
                        print(f"globals.RefSpectrum_DarkCorr length: {len(globals.RefSpectrum_DarkCorr)}")
                        
                        self.auto_save(filename, "RefDarkCorr", globals.RefSpectrum_DarkCorr)
                        
                        #####################################
                        '''
                        Stray Light Suppression (SLS)
                        Need the ctypes double-array spectrum as input for the function
                            AVS_SuppressStrayLight
                        Tested on spectrometer that has SLS feature
                        '''
                        ArrayType = ctypes.c_double * 4096 ## ctypes array
                        globals.RefSpectrum_DarkCorr_doublearray = ArrayType(*globals.RefSpectrum_DarkCorr) ## convert list to ctypes array
                        print(f"globals.RefSpectrum_DarkCorr_doublearray type: {type(globals.RefSpectrum_DarkCorr_doublearray)}")
                        
                        SLSfactor = 1
                        ret_code, globals.RefSpectrum_DarkSLSCorr =  ava.AVS_SuppressStrayLight(globals.dev_handle, 
                                                          SLSfactor,
                                                          globals.RefSpectrum_DarkCorr_doublearray)
                        print(f"return code: {ret_code}")
                        print(f"globals.RefSpectrum_DarkSLSCorr type: {type(globals.RefSpectrum_DarkSLSCorr)}")
                        print(f"globals.RefSpectrum_DarkSLSCorr length: {len(globals.RefSpectrum_DarkSLSCorr)}")
                        print(f"globals.RefSpectrum_DarkSLSCorr:\n{globals.RefSpectrum_DarkSLSCorr}")

                        self.auto_save(filename, "RefDarkSLSCorr", globals.RefSpectrum_DarkSLSCorr)

                    elif globals.MeasurementType == "Measurement":
                        globals.ScopeSpectrum_doublearray = globals.spectraldata
                        globals.ScopeSpectrum = globals.ScopeSpectrum_doublearray[:globals.pixels]
                        FileObject_Int = filename+"_Int_"+str(globals.m_Measurements)+".csv"
                        data_Int_vstack = np.vstack((globals.wavelength,
                                                     globals.ScopeSpectrum))
                        data_Int_transposed = np.transpose(data_Int_vstack)
                        xydata_Int = pd.DataFrame(data_Int_transposed,columns=["Wavelength (nm)","Pixel values"])
                        xydata_Int.to_csv(FileObject_Int,index=False)
                        #### Dark Correction
                        globals.ScopeSpectrum_DarkCorr = [globals.ScopeSpectrum_doublearray[x] - globals.DarkSpectrum_doublearray[x] for x in range(globals.pixels)]
                        print(f"globals.ScopeSpectrum_DarkCorr type: {type(globals.ScopeSpectrum_DarkCorr)}")
                        FileObject_IntDarkCorr = filename+"_IntDarkCorr_"+str(globals.m_Measurements)+".csv"
                        data_IntDarkCorr_vstack = np.vstack((globals.wavelength,
                                                     globals.ScopeSpectrum_DarkCorr))
                        data_IntDarkCorr_transposed = np.transpose(data_IntDarkCorr_vstack)
                        xydata_IntDarkCorr = pd.DataFrame(data_IntDarkCorr_transposed,columns=["Wavelength (nm)","Pixel values (DarkCorr)"])
                        xydata_IntDarkCorr.to_csv(FileObject_IntDarkCorr,index=False)
                    else:
                        self.statusBar.showMessage("Incorrect MeasurementType. {0:d})".format(lerror))
                    ##################
                    ######################################################
                    globals.saturated = ava.AVS_GetSaturatedPixels(globals.dev_handle)
                    SpectrumIsSatured = False
                    j = 0
                    while j < (globals.stoppixel - globals.startpixel):
                        SpectrumIsSatured = SpectrumIsSatured or globals.saturated[j]
                        j += 1
                        self.SaturatedChk.setChecked(SpectrumIsSatured)
                    # self.plot.update_plot()
                    l_Dif = timestamp - globals.m_PreviousTimeStamp  # timestamps in 10 us ticks
                    globals.m_PreviousTimeStamp = timestamp ##!!! use this as timestamp
                    
                    if (globals.m_Measurements > 1):
                        globals.m_SummatedTimeStamps += l_Dif
                        self.LastScanEdt.setText("{0:.3f}".format(l_Dif/100.0))  # in millisec
                        timeperscan = float(globals.m_SummatedTimeStamps) / float(100.0 * (globals.m_Measurements - 1))
                        self.TimePerScanEdt.setText("{0:.3f}".format(timeperscan))
                    else:
                        self.LastScanEdt.setText("")
                        self.TimePerScanEdt.setText("")
                    l_Seconds = globals.m_DateTime_start.secsTo(QDateTime.currentDateTime())
                    self.TimeSinceStartEdt.setText("{0:d}".format(l_Seconds))
                    self.NrScansEdt.setText("{0:d}".format(globals.m_Measurements))
                    ###########################################
                    ###########################################
                    ##!!! ADD if-statements for
                    ## Intensity and Absorbance modes
                    ## if Abs
                    ## abs_data = np.log10(np.divide(data_ref, data)) ## but improve it (what filetype is globals.spectraldata??)

                    ###########################################
                    ###########################################
                    ##!!! TEST THIS: ####
                    # if (self.SingleRBtn.isChecked()):
                    #    self.StartMeasBtn.setEnabled(int(1) == globals.m_Measurements) 
                           ## enable Start Measurement button when 1 is equal to
                               ## the number of measured spectra (globals.m_Measurements)                   
                   ####             ####
                    
                    if (self.FixedNrRBtn.isChecked()):
                       self.StartMeasBtn.setEnabled(int(self.NrMeasEdt.text()) == globals.m_Measurements) 
                           ## enable Start Measurement button when the user-defined #meas (NrMeasEdt) is equal to
                               ## the number of measured spectra (globals.m_Measurements)
                else: # StoreToRam measurements
                ## REMOVE CODE?
                    l_AvgScantimeRAM = 0.0
                    self.statusBar.showMessage("Meas.Status: Reading RAM")
                    j = 0
                    while j < lerror:
                        timestamp, globals.spectraldata = ava.AVS_GetScopeData(globals.dev_handle)
                        # self.plot.update_plot()
                        l_Dif = timestamp - globals.m_PreviousTimeStamp  # timestamps in 10 us ticks
                        globals.m_PreviousTimeStamp = timestamp
                        if (j > 1):
                            globals.m_SummatedTimeStamps += l_Dif
                            self.LastScanEdt.setText("{0:.3f}".format(l_Dif/100.0))  # in millisec
                            timeperscan = float(globals.m_SummatedTimeStamps) / float(100.0 * (j - 1))
                            self.TimePerScanEdt.setText("{0:.3f}".format(timeperscan))
                        else:
                            self.LastScanEdt.setText("")
                            self.TimePerScanEdt.setText("")
                        l_Seconds = globals.m_DateTime_start.secsTo(QDateTime.currentDateTime())
                        self.TimeSinceStartEdt.setText("{0:d}".format(l_Seconds))
                        self.NrScansEdt.setText("{0:d}".format(j+1))
                        j += 1
                    self.statusBar.showMessage("Meas.Status: Finished Reading RAM")    
                    self.StartMeasBtn.setEnabled(True)    
        else:
            self.statusBar.showMessage("Meas.Status: failed. {0:d})".format(lerror))
            globals.m_Failures += 1
        self.NrFailuresEdt.setText("{0:d}".format(globals.m_Failures))    
        return

    # @pyqtSlot(int, int)
    # def handle_dstrstatus(self, ldev_handle, lstatus):
    #     if (ldev_handle == globals.dev_handle): 
    #         globals.mDstrRecvCount += 1
    #         self.on_DstrStatusUpdateBtn_clicked()
    #     if (lstatus > 0):
    #         self.StartMeasBtn.setEnabled(True)
    #     return

    # @pyqtSlot()
    # def on_DstrStatusUpdateBtn_clicked(self):
    #     l_DstrStatus = DstrStatusType()
    #     l_DstrStatus = AVS_GetDstrStatus(globals.dev_handle)
    #     if (self.DstrRBtn.isChecked() == True):
    #         self.DstrStatusRecvCountEdt.setText("{0:d}".format(globals.mDstrRecvCount))
    #         self.DstrTotalScansEdt.setText("{0:d}".format(l_DstrStatus.m_TotalScans))
    #         self.DstrUsedScansEdt.setText("{0:d}".format(l_DstrStatus.m_UsedScans))
    #         self.DstrFlagsEdt.setText("{0:08b}".format(l_DstrStatus.m_Flags))
    #         self.DssEvent_Chk.setChecked(l_DstrStatus.m_Flags & DSTR_STATUS_DSS_MASK)
    #         self.FoeEvent_Chk.setChecked(l_DstrStatus.m_Flags & DSTR_STATUS_FOE_MASK)
    #         self.IErrorEvent_Chk.setChecked(l_DstrStatus.m_Flags & DSTR_STATUS_IERR_MASK) 
    #         if (l_DstrStatus.m_TotalScans > 0):
    #             self.DstrProgBar.setRange(0, l_DstrStatus.m_TotalScans)
    #             self.DstrProgBar.setValue(l_DstrStatus.m_UsedScans)      
    #     return    

    @pyqtSlot()
    def on_ReadEepromBtn_clicked(self):
        '''
        Function is used upon activating the spectrometer, i.e. on_ActivateBtn_clicked
        It sets integration time and nr. averages to EEPROM default
        '''
        l_DeviceData = ava.DeviceConfigType()
        l_DeviceData = ava.AVS_GetParameter(globals.dev_handle, 63484)
        #### show measurement settings
        self.StartPixelEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_StartPixel))
        self.StopPixelEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_StopPixel))
        self.IntTimeEdt.setText("{0:.3f}".format(l_DeviceData.m_StandAlone_m_Meas_m_IntegrationTime)) ## sets integration time to EEPROM default
        l_FPGAClkCycles = l_DeviceData.m_StandAlone_m_Meas_m_IntegrationDelay
        l_NanoSec = 125.0*(l_FPGAClkCycles-1.0)/6.0
        self.IntDelayEdt.setText("{0:.0f}".format(l_NanoSec))
        self.AvgEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_NrAverages))
        self.SatDetEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_SaturationDetection))
        self.InternalTriggerBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 0)
        self.ExternalTriggerBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 1)
        ####
        self.DarkCorrChk.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable == 1)
        self.DarkCorrPercEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage))
        self.NrMeasEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Nmsr))                
        return

    @pyqtSlot()
    def on_WriteEepromBtn_clicked(self): 
        l_DeviceData = ava.DeviceConfigType()
        l_DeviceData = ava.AVS_GetParameter(globals.dev_handle, 63484)
        l_DeviceData.m_StandAlone_m_Meas_m_StartPixel = int(self.StartPixelEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_StopPixel =  int(self.StopPixelEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_IntegrationTime = float(self.IntTimeEdt.text())
        l_NanoSec = float(self.IntDelayEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0)
        l_DeviceData.m_StandAlone_m_Meas_m_NrAverages = int(self.AvgEdt.text())
        ###########################################
        if (self.InternalTriggerBtn.isChecked()):
            l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 0
        if (self.ExternalTriggerBtn.isChecked()):
            l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 1
        # if (self.SoftwareTriggerRBtn.isChecked()):
        #     l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 0
        # if (self.HardwareTriggerRBtn.isChecked()):
        #     l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 1
        # if (self.SingleScanTriggerRBtn.isChecked()):
        #     l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 2
        # l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source = self.SynchTriggerRBtn.isChecked()
        # l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType = self.LevelTriggerRBtn.isChecked()
        ###########################################
        l_DeviceData.m_StandAlone_m_Meas_m_SaturationDetection = int(self.SatDetEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked()
        l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage = int(self.DarkCorrPercEdt.text())
        # l_DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix = int(self.SmoothNrPixelsEdt.text())
        # l_DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel = int(self.SmoothModelEdt.text())
        # l_DeviceData.m_StandAlone_m_Meas_m_Control_m_StrobeControl = int(self.FlashesPerScanEdt.text())
        # l_NanoSec = float(self.LaserDelayEdt.text())
        # l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserDelay = int(6.0*l_NanoSec/125.0)
        # l_NanoSec = float(self.LaserWidthEdt.text())
        # l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWidth = int(6.0*l_NanoSec/125.0)
        # l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWaveLength = float(self.LaserWavEdt.text())
        # l_DeviceData.m_StandAlone_m_Meas_m_Control_m_StoreToRam = int(self.NrStoreToRamEdt.text())
        ####
        l_DeviceData.m_StandAlone_m_Nmsr = int(self.NrMeasEdt.text())
        # write measurement parameters
        # debug = ctypes.sizeof(l_DeviceData)
        l_Ret = ava.AVS_SetParameter(globals.dev_handle, l_DeviceData)
        if (0 != l_Ret):
            QMessageBox.critical(self, "Qt Demo", "AVS_SetParameter failed, code {0:d}".format(l_Ret))
        return        

    @pyqtSlot()
    def on_SpectrometerList_clicked(self):
        if (len(self.SpectrometerList.selectedItems()) != 0):
            self.UpdateButtons()
        return      

    def ConnectGui(self):
        '''
        Functions is activated upon activating the connection with the spectrometer,
            i.e. by on_ActivateBtn_clicked
        '''
        versions = ava.AVS_GetVersionInfo(globals.dev_handle)
        self.FPGAVerEdt.setText("{}".format(str(versions[0],"utf-8")))
        self.FirmwareVerEdt.setText("{}".format(str(versions[1],"utf-8")))
        self.DLLVerEdt.setText("{}".format(str(versions[2],"utf-8")))
        globals.DeviceData = ava.DeviceConfigType()
        globals.DeviceData = ava.AVS_GetParameter(globals.dev_handle, 63484)
        lDetectorName = ava.AVS_GetDetectorName(globals.dev_handle, globals.DeviceData.m_Detector_m_SensorType)
        a_DetectorName = str(lDetectorName,"utf-8").split("\x00") 
        self.DetectorEdt.setText("{}".format(a_DetectorName[0]))
        if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_HAMS9201):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(True)  # LowNoise default for HAMS9201
            self.HighSensitivityRBtn.setChecked(False)
            ava.AVS_SetSensitivityMode(globals.dev_handle, 0)
        if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_TCD1304):    
            self.PreScanChk.show()    
            self.PreScanChk.setCheckState(Qt.Checked)
            l_Res = ava.AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked()) 
        if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU256LSB):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(False)
            self.HighSensitivityRBtn.setChecked(True)  # High Sensitive default for SU256LSB
            l_Res = ava.AVS_SetSensitivityMode(globals.dev_handle, 1)
        if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU512LDB):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(False)
            self.HighSensitivityRBtn.setChecked(True)  # High Sensitive default for SU512LDB
            l_Res = ava.AVS_SetSensitivityMode(globals.dev_handle, 1) 
        if (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_HAMG9208_512):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(True)  # low noise default
            self.HighSensitivityRBtn.setChecked(False)
            l_Res = ava.AVS_SetSensitivityMode(globals.dev_handle, 0) 
        globals.pixels = globals.DeviceData.m_Detector_m_NrPixels
        self.NrPixelsEdt.setText("{0:d}".format(globals.pixels))
        globals.startpixel = globals.DeviceData.m_StandAlone_m_Meas_m_StartPixel
        globals.stoppixel = globals.DeviceData.m_StandAlone_m_Meas_m_StopPixel
        globals.wavelength_doublearray = ava.AVS_GetLambda(globals.dev_handle) ## wavelength data here
        print(f"globals.wavelength_doublearray: {globals.wavelength_doublearray}")
        ##!!! CONVERT TO ARRAY HERE? like KMP
            ## self.wavelength = np.array(ret[:globals.pixels])
            ## np_round_to_tenths = np.around(self.wavelength, 1)
            ## globals.wavelength = list(np_round_to_tenths)

        return

    def DefaultSettings(self):
        '''
        ava.MeasConfigType() contains specific configuration and gets used with ret = AVS_PrepareMeasure
        '''
        self.measconfig = ava.MeasConfigType() 
        self.measconfig.m_StartPixel = globals.startpixel
        self.measconfig.m_StopPixel = globals.stoppixel
        
        l_NanoSec = float(self.IntDelayEdt.text())
        self.measconfig.m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0)
        print(f"self.measconfig.m_IntegrationDelay: {self.measconfig.m_IntegrationDelay}")
        
        self.measconfig.m_IntegrationTime = 3 # default integration time (ms)
        print(f"self.measconfig.m_IntegrationTime: {self.measconfig.m_IntegrationTime}")
        self.IntTimeEdt.setText(f"{self.measconfig.m_IntegrationTime:0.1f}") 
        
        self.measconfig.m_NrAverages = 100
        self.AvgEdt.setText(f"{self.measconfig.m_NrAverages:0d}") ## default # averages
        
        self.measconfig.m_CorDynDark_m_Enable = 1
        self.DarkCorrChk.setChecked(True)

        self.measconfig.m_CorDynDark_m_ForgetPercentage = 100
        self.DarkCorrPercEdt.setText(f"{self.measconfig.m_CorDynDark_m_ForgetPercentage:0d}")
        
        self.measconfig.m_SaturationDetection = 1
        self.SatDetEdt.setText(f"{self.measconfig.m_SaturationDetection:0d}")
        self.measconfig.m_Trigger_m_Mode = 0
        self.InternalTriggerBtn.setChecked(True)
        
        self.NrMeasEdt.setText("1") ## default 1 measurement
        
        globals.filename = "tests/20250825/TEST"
        print(f"DefaultSettings === globals.filename: {globals.filename}")
        
    def DisconnectGui(self):
        self.DetectorEdt.clear()
        self.NrPixelsEdt.clear()
        self.FPGAVerEdt.clear()
        self.FirmwareVerEdt.clear()
        self.DLLVerEdt.clear()
        self.DeviceTypeEdt.clear()
        self.ActivateBtn.setEnabled(False)
        self.DeactivateBtn.setEnabled(False)
        self.DigitalIoBtn.setEnabled(False)
        self.AnalogIoBtn.setEnabled(False)
        self.ShowEepromBtn.setEnabled(False)
        self.ReadEepromBtn.setEnabled(False)
        self.WriteEepromBtn.setEnabled(False)
        self.StartMeasBtn.setEnabled(False)
        # self.DstrStatusUpdateBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(False)
        self.ResetSpectrometerBtn.setEnabled(False)
        return

    def UpdateButtons(self):
        s = self.SpectrometerList.item(self.SpectrometerList.currentRow(), 1).text()
        self.ActivateBtn.setEnabled(s == "USB_AVAILABLE" or s == "ETH_AVAILABLE")
        self.DeactivateBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.DigitalIoBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.AnalogIoBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.ShowEepromBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.ReadEepromBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.WriteEepromBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")       
        self.StartMeasBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        # self.DstrStatusUpdateBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.StopMeasBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.ResetSpectrometerBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        return 

    @pyqtSlot()
    def on_DeactivateBtn_clicked(self):
        ret = ava.AVS_Deactivate(globals.dev_handle)
        globals.dev_handle = ava.INVALID_AVS_HANDLE_VALUE
        self.on_UpdateListBtn_clicked()
        self.DisconnectGui()
        return

    @pyqtSlot()
    def on_AnalogIoBtn_clicked(self):
        w2 = analog_io_demo.AnalogIoDialog(self)
        w2.show()
        return

    @pyqtSlot()
    def on_DigitalIoBtn_clicked(self):
        w3 = digital_io_demo.DigitalIoDialog(self)
        w3.show()
        return

    @pyqtSlot()
    def on_ShowEepromBtn_clicked(self):
        w4 = eeprom_demo.EepromDialog(self)
        w4.show()        
        return

    @pyqtSlot()
    def on_ResetSpectrometerBtn_clicked(self):
        l_Ret = ava.AVS_ResetDevice( globals.dev_handle)
        if (0 != l_Ret):
            QMessageBox.critical(self, "Qt Demo", "AVS_ResetDevice failed, code {0:d}".format(l_Ret))
        else:
            self.on_CloseCommBtn_clicked()    
        return

    @pyqtSlot()
    def on_DisableGraphChk_stateChanged(self):
        globals.m_GraphicsDisabled = self.DisableGraphChk.isChecked()
        return        

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget{font-size:10px}")
    app.lastWindowClosed.connect(app.quit)
    app.setApplicationName("PyQt5 full demo")
    form = QtdemoClass()
    form.show()
    app.exec_()

main()
