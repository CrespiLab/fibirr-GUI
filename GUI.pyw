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
- the file "MainWindow.py" contains the code that builds the GUI: it was created from MainWindow.ui
    -- the function "connectSlotsByName" connects signals to slots according to a simple naming convention
        --- https://riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html#connecting-slots-by-name
        --- "Signal" to on_"Slot"_valueChanged (works apparently for _clicked as well)
        --- @pyqtSlot() is necessary to specify which of the possible overloaded Qt signals should be connected to the slot


TO DO/ADD:
[DONE] Shutter control: OPEN-MEASURE-CLOSE 
[DONE] Shutter control over multiple measurements (user-input)
[DONE] Add parameters: Interval (s); Number of Cycles; ...

[DONE] Add "Dynamic Dark Correction"
    => already done: measconfig.m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked() ## turns on Dynamic Dark Correction
    [DONE] Change name of feature in GUI to Dynamic Dark Correction

[DONE] Add "Stray Light Suppression/Correction": 
    - [DONE] Ask Avantes: need the .py source code of the Qt_Demo_SLS compiled programme => does not exist...
    - [DONE] Check the C++ code for inspiration and apply AVS_SuppressStrayLight in .py

[DONE] "Record Reference" button that stores reference data (as np array) to be used here
[DONE] "Record Dark" button that stores dark data and creates a dark-corrected Intensity spectrum by subtraction
[DONE] Absorbance Mode
[DONE] Save spectra: Intensity and Absorbance separately
[] Add option to choose Reference data (from file) for current measurement
###
[DONE] Measurement mode: Irradiation Kinetics
    - [DONE] Need to add Arduino control for LED driver
[DONE] Add MOD mode feature => LED Control
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
[DONE] Remove * imports (convert to regular "full" imports)

"""
# import inspect
import sys
import ctypes
import time
import serial ## for communication with Arduino COM port

import numpy as np
import pandas as pd
from math import log10

from PyQt5.QtCore import (QTimer, pyqtSignal, pyqtSlot, QDateTime, Qt, 
                          QObject, QThread)
from PyQt5.QtWidgets import (QMainWindow, QAbstractItemView, QTableWidgetItem, 
                             QMessageBox, QListWidget, qApp, QFileDialog, QApplication)

import avaspec as ava
import globals
from UIs import MainWindow
import analog_io_demo
import digital_io_demo
import eeprom_demo
import user.settings as Settings
import tools.LED_control as LEDControl

##############################
######## add to globals.py
SHUTTER_OPEN = 1 ## value to open shutter
SHUTTER_CLOSE = 0 ## value to close shutter
##!!! TEST AND FIND OPTIMAL DELAY TIME FOR SHUTTER

    ## add to on_ActivateBtn_clicked
portID_pin12_DO4 = 3 ## portID of pin that controls the shutter
    ## re-name to PortID_InternalLightSource = 3

## see digital_io_demo.py for SetDigOut information
########

##############################
#############################
class Worker(QObject):
    finished = pyqtSignal()
    func = None
    def run(self):
        self.func()
        self.finished.emit()
        return

class MainWindow(QMainWindow, MainWindow.Ui_MainWindow):
    timer = QTimer() 
    SPECTR_LIST_COLUMN_COUNT = 4
    newdata = pyqtSignal(int, int) ## define new signal as a class attribute # (int,int) for callback
        ## is used below in __init__
    cancel = pyqtSignal()
    cancelled = False
    
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        #self.setWindowIcon() ##!!! add icon here or in Designer
        # self.showMaximized()
        
        #self.PreScanChk.hide()
        #self.SetNirSensitivityRgrp.hide()
        self.setStatusBar(self.statusBar)
        self.tabWidget.setCurrentWidget(self.CommunicationTab)
        self.SpectrometerList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.SpectrometerList.setColumnWidth(0,70)
        self.SpectrometerList.setColumnWidth(1,200)
        self.SpectrometerList.setColumnWidth(2,175)
        self.SpectrometerList.setColumnWidth(3,150)
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
        self.KineticsRBtn.setChecked(False)
        self.ContinuousRBtn.setChecked(False)
        self.IrrKinRBtn.setChecked(False)
        self.Mode_Scope.setChecked(True)
        self.Mode_Absorbance.setChecked(False)
        ###########################################
        self.SpectrometerList.clicked.connect(self.on_SpectrometerList_clicked)
#       self.OpenCommBtn.clicked.connect(self.on_OpenCommBtn_clicked)
    #       for buttons, do not use explicit connect together with the on_ notation, or you will get
    #       two signals instead of one!
        
        self.timer.timeout.connect(self.update_plot) ## This signal is emitted when the timer times out.
        self.timer.stop() ## Stops the timer.
        
        ###########################################
        self.newdata.connect(self.handle_newdata) ## 
            ## this connects signal: pyqtSignal(int, int)
                ## to slot: self.handle_newdata
        ###########################################
        self.cancel.connect(self.cancel_meas)
        self.DisableGraphChk.stateChanged.connect(self.on_DisableGraphChk_stateChanged)
        ava.AVS_Done()
        
        self.delay_acq = 0 ## time that acquisition takes
        ###########################################
     
    ###########################################
    ###########################################
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
                    ## sets integration time and nr. averages to EEPROM default
                self.StartLEDControl() ## initialise Arduino, etc.
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
    ###########################################

    @pyqtSlot()
    def on_DarkMeasBtn_clicked(self):
        print("on_DarkMeasBtn_clicked")
        globals.MeasurementType = "Dark"
        ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)
        ###########################################
        # globals.l_NrOfScans = int(1) # 1 scan
        ###########################################
        if (self.DarkMeasBtn.isEnabled()):
            print ("on_DarkMeasBtn_clicked === DarkMeasBtn enabled")
            globals.m_DateTime_start = QDateTime.currentDateTime()
            globals.m_SummatedTimeStamps = 0.0
            globals.m_Measurements = 0
            globals.m_Cycle = 1
            globals.m_Failures = 0
            self.TimeSinceStartEdt.setText("{0:d}".format(0))
            self.CycleNr.setText("{0:d}".format(0))
            self.NrFailuresEdt.setText("{0:d}".format(0))
        self.DarkMeasBtn.setEnabled(False) 

        # print(f"globals.m_Measurements: {globals.m_Measurements}")

        ret = ava.AVS_Measure(globals.dev_handle, 0, 1)
        globals.dataready = False
        print(f"globals.dataready: {globals.dataready}")
        self.Shutter_Close()
        
        while (globals.dataready == False):
            globals.dataready = (ava.AVS_PollScan(globals.dev_handle) == True)
            time.sleep(0.001)
        if globals.dataready == True:
            self.newdata.emit(globals.dev_handle, ret)
            time.sleep(self.delay_acq)

        print("Dark Measurement done")
        self.DarkMeasBtn.setEnabled(True)
        return

##!!! ADD provision that Dark Measurement needs to have been carried out
    @pyqtSlot()
    def on_RefMeasBtn_clicked(self):
        print("on_RefMeasBtn_clicked")
        globals.MeasurementType = "Ref"
        self.StartMeasBtn.setEnabled(False) 
        ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)
        ###########################################
        if (self.RefMeasBtn.isEnabled()):
            print ("on_RefMeasBtn_clicked === RefMeasBtn enabled")
            globals.m_DateTime_start = QDateTime.currentDateTime()
            globals.m_SummatedTimeStamps = 0.0
            globals.m_Measurements = 0
            globals.m_Cycle = 1
            globals.m_Failures = 0
            self.TimeSinceStartEdt.setText("{0:d}".format(0))
            self.CycleNr.setText("{0:d}".format(0))
            self.NrFailuresEdt.setText("{0:d}".format(0))
        self.RefMeasBtn.setEnabled(False)
        # self.timer.start(200) ### Starts or restarts the timer with a timeout interval of msec milliseconds.
        
        self.One_Measurement()
        
        self.RefMeasBtn.setEnabled(True)
        self.StartMeasBtn.setEnabled(True) ## enable Start Measurement button
        return

    @pyqtSlot()
    def on_StartMeasBtn_clicked(self):
        globals.MeasurementType = "Measurement"
        print("=== StartMeasBtn clicked ===")
        
        if (self.StartMeasBtn.isEnabled()):
            globals.m_DateTime_start = QDateTime.currentDateTime()
            globals.m_SummatedTimeStamps = 0.0
            globals.m_Measurements = 0
            globals.m_Cycle = 1
            globals.m_Failures = 0
            self.TimeSinceStartEdt.setText("{0:d}".format(0))
            self.CycleNr.setText("{0:d}".format(0))
            self.NrFailuresEdt.setText("{0:d}".format(0))

        # self.timer.start(200) ### Starts or restarts the timer with a timeout interval of msec milliseconds.
        
        ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)

        ###!!! in case of Absorbance Mode: add an if-check for the Ref having been measured
        ## if (self.AbsorbanceMode.isChecked()):
            ## if Ref is None:
                ## QMessageBox.warning(self, "Error", "Wrong input percentage")

        ######################################################################
        ### QThread functionality ###
        try:
            if self.thread_meas.isRunning():
                print("Shutting down running thread.")
                self.thread_meas.terminate()
                time.sleep(1)
            else:
                print("No thread was running.")
        except:
            print("Didn't find thread.")

        self.thread_meas = QThread() # this creates an additional computing thread for processes, so the main window doesn't freeze
        self.worker_meas = Worker() # this is a worker that will tell when the job is done
        
        if (self.SingleRBtn.isChecked()): ## added
            globals.AcquisitionMode = "Single" 
            # globals.l_NrOfScans = int(1)
            self.worker_meas.func = self.Single_Measurement #here the job of the worker is defined

        if (self.ContinuousRBtn.isChecked()):
            globals.AcquisitionMode = "Cont" 
            if self.NrCyclesEdt.text() == "0":
                globals.l_NrOfCycles = 10000
            else:
                globals.l_NrOfCycles = int(self.NrCyclesEdt.text())
            self.worker_meas.func = self.Continuous_Measurement #here the job of the worker is defined

        if (self.KineticsRBtn.isChecked()):
            globals.AcquisitionMode = "Kin"
            
            ##!!! ADD WARNING:
                ## if l_interval < 2
                ## choose Continuous Mode

            globals.l_NrOfCycles = int(self.NrCyclesEdt.text())
            globals.l_interval = int(self.Interval.text())
            self.worker_meas.func = self.Kinetics_Measurement #here the job of the worker is defined
            
            ##!!! before start, just in case: TURN OFF LED AND SHOW MESSAGE

        if (self.IrrKinRBtn.isChecked()):
            if Settings.twelvebit_adjusted_int == 0:
                QMessageBox.critical(self, "LED Control", "No or wrong LED current chosen")
            elif self.selected_LED is None:
                QMessageBox.critical(self, "LED Control", "No LED chosen")
            else:            
                globals.AcquisitionMode = "IrrKin" 
                globals.l_NrOfCycles = int(self.NrCyclesEdt.text())
                globals.l_interval = int(self.Interval.text())
                
                #!!! MAKE SLIDER AND PERCENTAGE FIELD INACTIVE DURING MEASUREMENT
                
                self.worker_meas.func = self.IrradiationKinetics_Measurement #here the job of the worker is defined. 

        #######################################################################
        if self.worker_meas.func is not None:
            self.worker_meas.moveToThread(self.thread_meas) #the workers job is moved from the frontend to the thread in backend
            self.thread_meas.started.connect(self.worker_meas.run) # when the thread is started, the worker runs
            self.worker_meas.finished.connect(self.thread_meas.quit) # when the worker is finished, the thread is quit
            self.worker_meas.finished.connect(self.worker_meas.deleteLater)
            self.thread_meas.finished.connect(self.thread_meas.deleteLater)
            self.thread_meas.start() #here the thread is actually started
            print("Finished thread setup.")
        else:
            print("self.worker_meas.func is None")
        return

##!!! maybe make a function for the dark measurement
    # def Dark_Measurement(self):
        

    @pyqtSlot()
    def One_Measurement(self):
        ##!!! FIX apparent issue with delays: Continuous mode has higher intensity
        
        print("=== One_Measurement ===")
        ###########################################        
        ret = ava.AVS_Measure(globals.dev_handle, 0, 1)
        globals.dataready = False
        print(f"globals.dataready: {globals.dataready}")
        if globals.AcquisitionMode != "Continuous":
            self.Shutter_Open()
        
        while (globals.dataready == False):
            globals.dataready = (ava.AVS_PollScan(globals.dev_handle) == True)
            time.sleep(0.001)
        if globals.dataready == True:
            self.newdata.emit(globals.dev_handle, ret)
            # print(f"sleeping after newdata emit for {self.delay_acq} s")
            time.sleep(self.delay_acq)
        
        if globals.AcquisitionMode != "Continuous":
            self.Shutter_Close()
        print("One Measurement done")
        print(f"globals.m_Measurements: {globals.m_Measurements}")
        return

    @pyqtSlot()
    def Single_Measurement(self):
        print("=== Single_Measurement ===")
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(True)
        self.cancelled = False

        if self.cancelled == True: ## break loop if Stop button was pressed
            print("Stopped Measurement")
            self.Shutter_Close()
            return
        else:
            self.One_Measurement()
        print("Single Measurement done")
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        return

    @pyqtSlot()
    def Continuous_Measurement(self):
        print("=== Continuous_Measurement ===")
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(True)
        nummeas = globals.l_NrOfCycles + 1 ## nr of measurements (1 more than nr of cycles)
        self.cancelled = False
        self.Shutter_Open()
        
        print(f"===nummeas: {nummeas}")
        for i in range(nummeas):
            if self.cancelled == True: ## break loop if Stop button was pressed
                print("Stopped Measurement")
                self.Shutter_Close()
                return
            else:
                self.One_Measurement()

        print("Continuous Measurement done")
        self.Shutter_Close()
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        return


    @pyqtSlot()
    def Kinetics_Measurement(self):
        print("=== Kinetics_Measurement ===")
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(True)
        nummeas = globals.l_NrOfCycles + 1 ## nr of measurements (1 more than nr of cycles)
        print(f"globals.delays_aroundShutter: {globals.delays_aroundShutter}")
        delay = int(globals.l_interval - globals.delays_aroundShutter)
        self.cancelled = False
        
        print(f"nummeas: {nummeas}")
        for i in range(nummeas):
            if self.cancelled == True: ## break loop if Stop button was pressed
                print("Stopped Kinetic Measurement")
                self.Shutter_Close()
                return
            else:
                self.One_Measurement()
                if globals.m_Measurements != nummeas:
                    print(f"Waiting for {delay} s")
                    for t in range(delay):
                        time.sleep(1)
                        print(f"Slept for 1 second. t = {t}")
                        if self.cancelled == True:
                            break
                    print(f"Delay {delay} s done")
        print(f"Kinetic measurement done ({nummeas} measurements)")
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        return

    @pyqtSlot()
    def IrradiationKinetics_Measurement(self):
        ''' 
        The interval defined by the user is used for the delay,
            i.e. it is the actual irradiation time.
        There are some delays around spectral acquisition.
        '''
        print("=== IrradiationKinetics_Measurement ===")
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(True)
        nummeas = globals.l_NrOfCycles + 1 ## nr of measurements (1 more than nr of cycles)
        
        print(f"globals.delays_total: {globals.delays_total}")
        
        delay = globals.l_interval ## delay is irradiation time (user-defined)
        ##!!! MAYBE CHANGE BACK TO DELAY WITH DELAYS_TOTAL SUBTRACTED
        
        self.cancelled = False
        print(f"===nummeas: {nummeas}\n===LED {self.selected_LED}, {self.current} mA ({self.percentage} %)")

        ##!!! IMPORTANT:
            ## log actual irradiation time

        for i in range(nummeas):
            print(f"i: {i}")
            if self.cancelled == True: ## break loop if Stop button was pressed
                print("Cancelled IrradiationKinetics Measurement")
                self.Shutter_Close()
                self.turnLED_OFF()
                return
            else:
                self.One_Measurement() ## do one measurement
                if globals.m_Measurements != nummeas:
                    self.turnLED_ON() ## wait for a bit, and turn on LED
                    print(f"Waiting for {delay} s")
                    for t in range(delay):
                        time.sleep(1)
                        if self.cancelled == True:
                            break
                    print(f"Delay {delay} s done")
                    self.turnLED_OFF() ## turn off LED, and wait for a bit
        print(f"Irradiation Kinetics measurement done ({nummeas} measurements)")
        
        ##!!! ADD: SAVE LOG
            ## generate log file meant for autoQY: timestamps of actual irradiation times
        
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        return

    @pyqtSlot()
    def on_StopMeasBtn_clicked(self): 
        print("=== StopMeasBtn clicked ===")
        self.cancel.emit()
        time.sleep(1)
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        # self.timer.stop()
        return

    @pyqtSlot()
    def cancel_meas(self):
        ret = ava.AVS_StopMeasure(globals.dev_handle)
        self.cancelled = True
        return

    @pyqtSlot()
    def on_AutoSaveFolderBtn_clicked(self):
        print("=== SaveFolderBtn clicked ===")
        
        # options = QtWidgets.QFileDialog.Options()

        ## File dialog for selecting files
        folder = QFileDialog.getExistingDirectory(self,
                                                  "Choose folder for auto-saving", 
                                                  "",
                                                  QFileDialog.ShowDirsOnly)
        if folder:
            globals.AutoSaveFolder = folder
        else:
            print("No folder selected.")
            globals.AutoSavefolder = Settings.Default_AutoSaveFolder
            ##!!! PRINT MESSAGE: NO AUTO-SAVE FOLDER SELECTED: REVERTED TO BACK-UP
                ## CREATE BACK-UP FOLDER WITH NAME: DATE AND TIME
        
        self.update_label_AutoSaveFolder()
        return

    def update_label_AutoSaveFolder(self):
        self.Label_AutoSaveFolder.setText(globals.AutoSaveFolder)

    ###########################################################################
    ###########################################################################

##!!! TEST AND FIND OPTIMAL DELAY TIME (see DefaultSettings)
    def Shutter_Open(self):
        ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_OPEN) ## open shutter
        
        ##!!! ADD TIMESTAMP
        #globals.timestamps_ShutterOpen = 
                
        time.sleep(self.delay_afterShutter_Open) ## short delay between Open Shutter and Measure
        
        # print(">> Shutter_Open <<")

    def Shutter_Close(self):
        time.sleep(self.delay_beforeShutter_Close) ## short delay between Measure and Close Shutter
        ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
        
        ##!!! ADD TIMESTAMP
        #globals.timestamps_ShutterClose = 
        
        time.sleep(self.delay_afterShutter_Close) ## short delay after Close Shutter
        
        # print(">> Shutter Closed <<")

    ###########################################################################
    ###########################################################################

    def StartLEDControl(self):
        ''' LED Control '''
        globals.ArduinoCOMport = Settings.Default_ArduinoCOMport
        
        self.selected_LED = None
        self.percentage = 0 # start with 0%
        self.current = 0
        
        self.delay_beforeLED_ON = 400/1000 ## delay (ms) before turning on LED
        self.delay_afterLED_OFF = 1300/1000 ## delay (ms) after turning off LED
        globals.delays_aroundLED = self.delay_beforeLED_ON + self.delay_afterLED_OFF

        #### drop-down menu ####
        self.DropDownBox_LEDs.addItems(list(Settings.MaxCurrents.keys()))
        self.DropDownBox_LEDs.currentIndexChanged.connect(self.update_dropdown)

        self.LEDPercentageEdt.setText(str(self.percentage)) # 
        self.LEDPercentageEdt.textChanged.connect(self.update_percentage)

        #### slide bar ####
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(100)
        self.horizontalSlider.setValue(self.percentage)
        self.horizontalSlider.valueChanged.connect(self.update_slider)

        try:
            LEDControl.initialise_Arduino() ## start communication with Arduino
            self.update_dropdown() # Initial calculation
            self.on_LED_off_manual_clicked() # extra caution
            self.SpectrometerList.setItem(0, 3, QTableWidgetItem("SUCCESS")) 
        except serial.serialutil.SerialException as e:
            QMessageBox.critical(self, "LED INITIALISATION FAILED", f"{e}")
            self.SpectrometerList.setItem(0, 3, QTableWidgetItem("FAIL")) 
        except:
            QMessageBox.critical(self, "LED INITIALISATION FAILED", "unkown error")
            self.SpectrometerList.setItem(0, 3, QTableWidgetItem("FAIL")) 

    @pyqtSlot()
    def on_StartLEDControlBtn_clicked(self):
        self.StartLEDControl()

    @pyqtSlot()
    def on_SetLEDsettings_clicked(self):
        self.update_calculation()
        self.update_label_CurrentCurrent()
        self.update_label_CurrentPercentage()

    @pyqtSlot()
    def on_LED_on_manual_clicked(self):
        msg = QMessageBox()
        msg.setWindowTitle("Please Confirm")
        msg.setText("Are you sure you want to turn ON the LED?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.buttonClicked.connect(self.LED_on_manual_warning)
        msg.exec_() # Execute the dialog

    @pyqtSlot()
    def on_LED_off_manual_clicked(self):
        self.turnLED_OFF()

    def LED_on_manual_warning(self, i):
        if i.text() == "&Yes":
            if Settings.twelvebit_adjusted_int == 0:
                QMessageBox.warning(self, "Error", "Wrong input percentage")
                return
            self.turnLED_ON()
        else:
            self.turnLED_OFF()

    def turnLED_ON(self):
        ##!!! ADDED DELAY
        if not (self.StartMeasBtn.isEnabled()): ## if on-going measurement
            time.sleep(self.delay_beforeLED_ON)
        LEDControl.turnLED_ON()
        
        ##!!! ADD
        ##globals.timestamp_LED_ON = 
        self.update_label_LEDstatus()

    def turnLED_OFF(self):
        LEDControl.turnLED_OFF()
        ##!!! ADD
        ##globals.timestamp_LED_OFF = 
        self.update_label_LEDstatus()
        if not (self.StartMeasBtn.isEnabled()): ## if on-going measurement
            time.sleep(self.delay_afterLED_OFF)
        ##!!! ADDED DELAY

    ###########################################################################
    ###########################################################################
    @pyqtSlot()
    def update_plot(self):
        if (self.DisableGraphChk.isChecked() == False):
            if (self.Mode_Scope.isChecked()):
                if globals.MeasurementType == "Dark":
                    self.plot.update_plot(globals.DarkSpectrum)
                elif globals.MeasurementType == "Ref":
                    self.plot.update_plot(globals.RefSpectrum_DarkSLSCorr) ## plot.py/update_plot
                elif globals.MeasurementType == "Measurement":
                    self.plot.update_plot(globals.ScopeSpectrum_DarkSLSCorr)
            elif (self.Mode_Absorbance.isChecked()):
                self.plot.update_absorbanceplot()
            else:
                QMessageBox.warning(self, "Error", "Something wrong with Measurement Mode")                
        return         

    @pyqtSlot()
    def auto_save(self, foldername, mode, spectrum):
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
        FileObject = f"{foldername}/{mode}.csv"
        data_vstack = np.vstack((globals.wavelength,
                                     spectrum))
        data_transposed = np.transpose(data_vstack)
        xydata = pd.DataFrame(data_transposed,columns=["Wavelength (nm)","Pixel values"])
        xydata.to_csv(FileObject,index=False)
        # print(f"{mode} spectrum auto-saved as {FileObject}")

        ##!!! IF FILE ALREADY EXISTS: ADD A NUMBER

        self.statusBar.showMessage(f"{globals.MeasurementType} Spectrum auto-saved as {FileObject}")


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
                    try:
                        # print(f"globals.dataready: {globals.dataready}")
                        globals.m_Measurements += 1
                        globals.m_Cycle += 1
                        timestamp = 0
                        timestamp, globals.spectraldata = ava.AVS_GetScopeData(globals.dev_handle) ## globals.spectraldata is array of doubles
                        # ##################
                        savefolder = globals.AutoSaveFolder
                        ##################
                        if globals.MeasurementType == "Dark":
                            globals.DarkSpectrum_doublearray = globals.spectraldata
                            globals.DarkSpectrum = globals.DarkSpectrum_doublearray[:globals.pixels]
                            self.auto_save(savefolder, "Dark", globals.DarkSpectrum)
                        elif globals.MeasurementType == "Ref":
                            globals.RefSpectrum_doublearray = globals.spectraldata
                            globals.RefSpectrum = globals.RefSpectrum_doublearray[:globals.pixels]
                            self.auto_save(savefolder, "Ref", globals.RefSpectrum)
                            
                            #### Dark-Corrected ####
                            globals.RefSpectrum_DarkCorr = [globals.RefSpectrum_doublearray[x] - globals.DarkSpectrum_doublearray[x] for x in range(globals.pixels)]
                            self.auto_save(savefolder, "Ref_DarkCorr", globals.RefSpectrum_DarkCorr)
                            
                            #####################################
                            '''
                            Stray Light Suppression (SLS)
                            Need the ctypes double-array spectrum as input for the function
                                AVS_SuppressStrayLight
                            Tested on spectrometer that has SLS feature
                            '''
                            ArrayType = ctypes.c_double * 4096 ## ctypes array
                            globals.RefSpectrum_DarkCorr_doublearray = ArrayType(*globals.RefSpectrum_DarkCorr) ## convert list to ctypes array
                            
                            SLSfactor = 1
                            ret_code, globals.RefSpectrum_DarkSLSCorr_doublearray =  ava.AVS_SuppressStrayLight(globals.dev_handle, 
                                                              SLSfactor,
                                                              globals.RefSpectrum_DarkCorr_doublearray)
                            globals.RefSpectrum_DarkSLSCorr = list(globals.RefSpectrum_DarkSLSCorr_doublearray) # convert to list
                            self.auto_save(savefolder, "Ref_DarkSLSCorr", globals.RefSpectrum_DarkSLSCorr)
                            
                            ##!!! SAVE ALL REFERENCE SPECTRA IN ONE FILE

                        elif globals.MeasurementType == "Measurement":
                            globals.ScopeSpectrum_doublearray = globals.spectraldata
                            globals.ScopeSpectrum = globals.ScopeSpectrum_doublearray[:globals.pixels]
                            
                            #### Dark Correction ####
                            globals.ScopeSpectrum_DarkCorr = [globals.ScopeSpectrum_doublearray[x] - globals.DarkSpectrum_doublearray[x] for x in range(globals.pixels)]
                            
                            #####################################
                            ############### SLS #################
                            #####################################
                            '''
                            Stray Light Suppression (SLS)
                            Need the ctypes double-array spectrum as input for the function
                                AVS_SuppressStrayLight
                            Tested on spectrometer that has SLS feature
                            '''
                            ArrayType = ctypes.c_double * 4096 ## ctypes array
                            globals.ScopeSpectrum_DarkCorr_doublearray = ArrayType(*globals.ScopeSpectrum_DarkCorr) ## convert list to ctypes array

                            ##!!! MAKE INTO A FUNCTION
                            SLSfactor = 1
                            ret_code, globals.ScopeSpectrum_DarkSLSCorr_doublearray =  ava.AVS_SuppressStrayLight(globals.dev_handle, 
                                                              SLSfactor,
                                                              globals.ScopeSpectrum_DarkCorr_doublearray)
                            globals.ScopeSpectrum_DarkSLSCorr = list(globals.ScopeSpectrum_DarkSLSCorr_doublearray) # convert to list
                            
                            ##!!! CHANGE MEASUREMENT NR HERE (OR IN AUTO-SAVE FUNCTION): add 0s; 0001, 0002, ..., 0118, etc.
                            
                            self.auto_save(savefolder, f"{globals.AcquisitionMode}_Int_{globals.m_Measurements}", globals.ScopeSpectrum)
                            self.auto_save(savefolder, f"{globals.AcquisitionMode}_Int_DarkCorr_{globals.m_Measurements}", globals.ScopeSpectrum_DarkCorr)
                            self.auto_save(savefolder, f"{globals.AcquisitionMode}_Int_DarkSLSCorr_{globals.m_Measurements}", globals.ScopeSpectrum_DarkSLSCorr)
                            
                            #####################################
                            ########## ABSORBANCE MODE ##########
                            #####################################
                            if (self.Mode_Absorbance.isChecked()): ## Absorbance mode
                                globals.AbsSpectrum_doublearray = [log10(globals.RefSpectrum_DarkSLSCorr_doublearray[x] / globals.ScopeSpectrum_DarkSLSCorr_doublearray[x]) if globals.ScopeSpectrum_DarkSLSCorr_doublearray[x]>0 and globals.RefSpectrum_DarkSLSCorr_doublearray[x]>0 else 0.0 for x in range(globals.pixels)]
                                globals.AbsSpectrum = list(globals.AbsSpectrum_doublearray)
                                self.auto_save(savefolder, f"{globals.AcquisitionMode}_Abs_{globals.m_Measurements}", globals.AbsSpectrum)

                        #####################################
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

                        l_MilliSeconds = globals.m_DateTime_start.msecsTo(QDateTime.currentDateTime()) ## difference in milliseconds between current and start time
                        l_Seconds = l_MilliSeconds/1000
                        print(f"handle_newdata timestamp: {l_Seconds} (s)")
                        
                        self.TimeSinceStartEdt.setText(f"{l_Seconds:.3f}")
                        self.CycleNr.setText(f"{globals.m_Cycle}")
                        ###########################################
                        self.update_plot() ## update plot
                    except (ValueError, RuntimeError, TypeError, NameError) as e:
                        print(f"new data was not handled completely\n   Type of Exception: {type(e)}\n   Message: {e}")
                    except:
                        print("new data was not handled completely (unknown error)")
                    return
                    ######################################################
        else:
            self.statusBar.showMessage("Meas.Status: failed. {0:d})".format(lerror))
            globals.m_Failures += 1
        self.NrFailuresEdt.setText("{0:d}".format(globals.m_Failures))    
        return

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
        self.NrCyclesEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Nmsr))                
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
        ###########################################
        l_DeviceData.m_StandAlone_m_Meas_m_SaturationDetection = int(self.SatDetEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked()
        l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage = int(self.DarkCorrPercEdt.text())
        ####
        l_DeviceData.m_StandAlone_m_Nmsr = int(self.NrCyclesEdt.text())
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

        ret = ava.AVS_UseHighResAdc(globals.dev_handle, True)
        ret = ava.AVS_EnableLogging(False)
            
        globals.pixels = globals.DeviceData.m_Detector_m_NrPixels
        self.NrPixelsEdt.setText("{0:d}".format(globals.pixels))
        globals.startpixel = globals.DeviceData.m_StandAlone_m_Meas_m_StartPixel
        globals.stoppixel = globals.DeviceData.m_StandAlone_m_Meas_m_StopPixel
        globals.wavelength_doublearray = ava.AVS_GetLambda(globals.dev_handle) ## wavelength data here
        # print(f"ConnectGui ==== globals.wavelength_doublearray: {globals.wavelength_doublearray}")
        globals.wavelength = globals.wavelength_doublearray[:globals.pixels]
        # print(f"ConnectGui ==== globals.wavelength: {globals.wavelength}")
        return

    def DefaultSettings(self):
        '''
        ava.MeasConfigType() contains specific configuration and gets used with ret = AVS_PrepareMeasure
        '''
        self.measconfig = ava.MeasConfigType() 
        self.measconfig.m_StartPixel = globals.startpixel
        self.measconfig.m_StopPixel = globals.stoppixel
        
        l_NanoSec = float(self.IntDelayEdt.text())
        self.measconfig.m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0) ## from Avantes
        self.measconfig.m_IntegrationTime = 3 # default integration time (ms)
        print(f"self.measconfig.m_IntegrationTime: {self.measconfig.m_IntegrationTime}")
        self.IntTimeEdt.setText(f"{self.measconfig.m_IntegrationTime:0.1f}") 
        
        self.measconfig.m_NrAverages = 100
        self.AvgEdt.setText(f"{self.measconfig.m_NrAverages:0d}") ## default # averages
        
        self.delay_acq = (self.measconfig.m_IntegrationTime * self.measconfig.m_NrAverages)/1000 # acquisition time (s)
        print(f"self.delay_acq: {self.delay_acq} s")
        
        self.delay_afterShutter_Open = 0.5 # seconds
        self.delay_beforeShutter_Close = 0.1 # seconds
        self.delay_afterShutter_Close = 0.1 # seconds
        
        print(f"self.delay_afterShutter_Open: {self.delay_afterShutter_Open} s")
        print(f"self.delay_beforeShutter_Close: {self.delay_beforeShutter_Close} s")
        print(f"self.delay_afterShutter_Close: {self.delay_afterShutter_Close} s")
        
        globals.delays_aroundShutter = self.delay_afterShutter_Open + self.delay_afterShutter_Close
        globals.delays_total = globals.delays_aroundLED + globals.delays_aroundShutter
        
        self.measconfig.m_CorDynDark_m_Enable = 1
        self.DarkCorrChk.setChecked(True)

        self.measconfig.m_CorDynDark_m_ForgetPercentage = 100
        '''
        From AvaSpec Libary Manual, Section 3.4.6:
        The Dark Correction Type structure includes an m_enable and m_ForgetPercentage field (see also
        section 2.6 on Data Elements). Measurements have shown that taking into account the historical dark
        scans, does not make much difference. The recommended value for m_ForgetPercentage is therefore 
        100.
        '''
        self.DarkCorrPercEdt.setText(f"{self.measconfig.m_CorDynDark_m_ForgetPercentage:0d}")
        
        self.measconfig.m_SaturationDetection = 1
        self.SatDetEdt.setText(f"{self.measconfig.m_SaturationDetection:0d}")
        self.measconfig.m_Trigger_m_Mode = 0
        self.InternalTriggerBtn.setChecked(True)
        
        self.NrCyclesEdt.setText("10") ## default nr. measurements
        self.Interval.setText("10") # default interval in seconds
        
        globals.AutoSaveFolder = Settings.Default_AutoSaveFolder 
        ##!!! SET DEFAULT
        
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
        self.StopMeasBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.ResetSpectrometerBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        return 
    
    ###########################################################################
    ############################ LED Control ##################################
    ###########################################################################

    def update_dropdown(self):
        self.selected_LED = self.DropDownBox_LEDs.currentText()
        self.MaxCurrent, Settings.twelvebit_max_thisLED = LEDControl.AdjustMaxCurrent(self.selected_LED) ## use currently selected LED
        self.update_label_MaxCurrent()

    def update_label_MaxCurrent(self):
        self.Label_MaxCurrent.setText(str(self.MaxCurrent))

    def update_slider(self):
        self.percentage = self.horizontalSlider.value()
        self.LEDPercentageEdt.setText(str(self.percentage)) # 

    def update_percentage(self):
        if self.LEDPercentageEdt.text() == '':
            self.percentage = 0
        elif 0 <= int(self.LEDPercentageEdt.text()) <= 100:
            self.percentage = int(self.LEDPercentageEdt.text())  # Convert the input to an integer
            self.horizontalSlider.setValue(self.percentage)
        else:
            self.percentage = 0
        print(f"updated percentage: {self.percentage}")

    def update_calculation(self):
        Settings.twelvebit_adjusted_int = LEDControl.percent_to_12bit(Settings.twelvebit_max_thisLED,
                                                                      int(self.percentage))
        Settings.twelvebit_adjusted = str(Settings.twelvebit_adjusted_int)
        print(f"update_calculation twelvebit_adjusted: {Settings.twelvebit_adjusted}")
        self.current = round((int(self.percentage) / 100) * self.MaxCurrent)

    def update_label_CurrentCurrent(self):
        if self.current is None:
            self.current = ''
        self.Label_CurrentCurrent.setText(str(self.current))
    
    def update_label_CurrentPercentage(self):
        self.Label_CurrentPercentage.setText(str(self.percentage))
    
    def update_label_LEDstatus(self):
        self.LED_DisplayStatus.setText(Settings.LEDstatus)

    ###########################################################################
    ###########################################################################
    ###########################################################################
    
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
    app.setApplicationName("fibirr-GUI")
    form = MainWindow()
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
