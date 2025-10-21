"""
Used the script PyQt5_fulldemo.pyw provided with the AvaSpec library as a starting example.

Notes:
- "MainWindow.py" contains the code that builds the GUI: it was created from MainWindow.ui using the tool pyuic5 from the package pyqt5-tools
- In the .ui file, the function "connectSlotsByName" connects signals to slots according to a simple naming convention
    -- https://riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html#connecting-slots-by-name
    -- For example, the function (Signal) "on_ActivateBtn_clicked(self)" is connected to the Slot "ActivateBtn"
    -- @pyqtSlot() is necessary to specify which of the possible overloaded Qt signals should be connected to the slot
    -- For buttons, do not use explicit connect together with the on_ notation, or you will get two signals instead of one!
    -- If you leave out the @pyqtSlot() line, you will also get an extra signal! So you might even get three!
"""
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
                             QMessageBox, QListWidget, QFileDialog, QApplication)

import avaspec as ava
import globals
from UIs import MainWindow
import analog_io_demo
import digital_io_demo
import eeprom_demo
import user.settings as Settings
import tools.LED_control as LEDControl
import tools.data_handling as DataHandling

###############################################################################

class Worker(QObject):
    finished = pyqtSignal()
    func = None
    def run(self):
        self.func()
        self.finished.emit()
        return

class MainWindow(QMainWindow, MainWindow.Ui_MainWindow):
    # timer = QTimer() 
    SPECTR_LIST_COLUMN_COUNT = 4
    newdata = pyqtSignal(int, int) ## define new signal as a class attribute # (int,int) for callback
        ## is connected to handle_newdata below in __init__
    cancel = pyqtSignal()
    cancelled = False
    
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        # self.setWindowIcon() ##!!! add icon here or in Designer
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
        self.DarkMeasBtn.setEnabled(False)
        self.RefMeasBtn.setEnabled(False)
        self.AbsorbanceModeBtn.setEnabled(False)
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(False)
        self.ResetSpectrometerBtn.setEnabled(False)        
        ###########################################
        self.ConnectUSBRBtn.setChecked(True)
        self.ConnectEthernetRBtn.setChecked(False)
        self.SingleRBtn.setChecked(True)
        self.KineticsRBtn.setChecked(False)
        self.ContinuousRBtn.setChecked(False)
        self.IrrKinRBtn.setChecked(False)
        self.ScopeModeBtn.setChecked(True)
        self.AbsorbanceModeBtn.setChecked(False)
        ###########################################
        self.SingleRBtn.toggled.connect(self.handle_radio_selection)
        self.ContinuousRBtn.toggled.connect(self.handle_radio_selection)
        self.KineticsRBtn.toggled.connect(self.handle_radio_selection)
        self.IrrKinRBtn.toggled.connect(self.handle_radio_selection)
        self.ScopeModeBtn.toggled.connect(self.handle_radio_selection)
        self.AbsorbanceModeBtn.toggled.connect(self.handle_radio_selection)
        self.PlotTraceChk.toggled.connect(self.handle_radio_selection)
        self.TraceWavelengthChk_1.toggled.connect(self.handle_radio_selection)
        self.TraceWavelengthChk_2.toggled.connect(self.handle_radio_selection)
        self.handle_radio_selection()
        
        self.ContinuousRBtn.setEnabled(False) ##!!! TURN ON WHEN FUNCTION IS READY
        ###########################################
        self.SpectrometerList.clicked.connect(self.on_SpectrometerList_clicked)
        # self.timer.timeout.connect(self.update_plot) ## This signal is emitted when the timer times out.
        # self.timer.stop() ## Stops the timer.
        ###########################################
        self.newdata.connect(self.handle_newdata) ## this connects signal: pyqtSignal(int, int), to slot: self.handle_newdata
        ###########################################
        self.cancel.connect(self.cancel_meas)
        self.DisableGraphChk.stateChanged.connect(self.on_DisableGraphChk_stateChanged)
        ava.AVS_Done()
        
        self.delay_acq = 0 ## time that acquisition takes
        ###########################################

    ###########################################
    ###########################################
    @pyqtSlot()
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

        return l_RequiredSize

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
                self.measconfig = ava.MeasConfigType() ## use avaspec class for measurement configuration
                m_Identity = l_Id
                globals.mSelectedDevRow = self.SpectrometerList.currentItem().row()
                self.on_UpdateListBtn_clicked()
                self.ConnectGui()
                self.on_ReadEepromBtn_clicked() ## sets integration time and nr. averages to EEPROM default
                self.StartLEDControl() ## initialise Arduino, etc.
                self.DefaultSettings() # set default settings
                ###########################################
                self.IntTimeEdt.textChanged.connect(self.handle_textfield_change)
                self.AvgEdt.textChanged.connect(self.handle_textfield_change)
                self.on_SettingsBtn_clicked()
                ###########################################
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
                ava.AVS_SetDigOut(globals.dev_handle, ava.PortID_Internal_LightSource, ava.SHUTTER_CLOSE) ## close shutter
        return m_Identity

    @pyqtSlot()
    def on_SettingsBtn_clicked(self):
        print("on_SettingsBtn_clicked")
        former_integration_time = self.measconfig.m_IntegrationTime ## save former value
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
        if self.SatDetEdt.text() == "on":
            self.measconfig.m_SaturationDetection = 1
        elif self.SatDetEdt.text() == "off":
            self.measconfig.m_SaturationDetection = 0
        ###########################################
        if (self.InternalTriggerBtn.isChecked()):
            self.measconfig.m_Trigger_m_Mode = 0
            ##!!! DEFINE m_Trigger_m_Mode = 0 : internal shutter of light source (change name?)
        if (self.ExternalTriggerBtn.isChecked()):
            self.measconfig.m_Trigger_m_Mode = 1
            ##!!! DEFINE m_Trigger_m_Mode = 1 : external Arduino-controlled shutter (change name?)
        self.StatusLabel_Settings.setText("Settings saved")
        if self.measconfig.m_IntegrationTime != former_integration_time: ## If Integration Time is changed (not Nr. Averages): need to re-record Dark and Ref
            print(f"Integration Time changed from {former_integration_time} to {self.measconfig.m_IntegrationTime}\nDark and Ref need to be re-recorded")
            self.reset_RefDark()
            ##!!! UNLOAD DARK AND REF
    ###########################################

    @pyqtSlot()
    def on_DarkMeasBtn_clicked(self):
        print("on_DarkMeasBtn_clicked")
        globals.MeasurementType = "Dark"
        ret = ava.AVS_PrepareMeasure(globals.dev_handle, self.measconfig)
        ###########################################
        if (self.DarkMeasBtn.isEnabled()):
            print ("on_DarkMeasBtn_clicked === DarkMeasBtn enabled")
            globals.m_DateTime_start = QDateTime.currentDateTime()
            globals.m_SummatedTimeStamps = 0.0
            globals.m_Measurements = 0
            globals.m_Cycle = 0
            globals.m_Failures = 0
            self.label_TimeSinceStart.setText("{0:d}".format(0))
            self.label_CurrentCycleNr.setText("{0:d}".format(0))
            self.label_NrFailures.setText("{0:d}".format(0))
        self.DarkMeasBtn.setEnabled(False) 

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
        self.StatusLabel_Dark.setText(u"\u2713") ## show checkmark
        self.DarkMeasBtn.setEnabled(True)
        self.RefMeasBtn.setEnabled(True)
        return

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
            globals.m_Cycle = 0
            globals.m_Failures = 0
            self.label_TimeSinceStart.setText("{0:d}".format(0))
            self.label_CurrentCycleNr.setText("{0:d}".format(0))
            self.label_NrFailures.setText("{0:d}".format(0))
        self.RefMeasBtn.setEnabled(False)
        self.One_Measurement()
        self.StatusLabel_Ref.setEnabled(True)
        self.StatusLabel_Ref.setText(u"\u2713") ## show checkmark
        self.RefMeasBtn.setEnabled(True)
        self.AbsorbanceModeBtn.setEnabled(True) ## enable Absorbance Mode
        self.StartMeasBtn.setEnabled(True) ## enable Start Measurement button
        return ret

    @pyqtSlot()
    def on_StartMeasBtn_clicked(self):
        globals.MeasurementType = "Measurement"
        print("=== StartMeasBtn clicked ===")
        
        if (self.StartMeasBtn.isEnabled()):
            globals.m_DateTime_start = QDateTime.currentDateTime()
            globals.m_SummatedTimeStamps = 0.0
            globals.m_Measurements = 0
            globals.m_Cycle = 0
            globals.m_Failures = 0
            self.label_TimeSinceStart.setText("{0:d}".format(0))
            self.label_CurrentCycleNr.setText("{0:d}".format(0))
            self.label_NrFailures.setText("{0:d}".format(0))
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
            self.logger = self.create_logger("log") ## initialise logger for timestamps
            self.recent_spectra_Abs = self.create_logger("allspectra_Abs")
            self.recent_spectra_Int = self.create_logger("allspectra_Int")
            self.save_recent_spectra()
            
            ##!!! ADD WARNING:
                ## if l_interval < 2
                ## choose Continuous Mode

            globals.l_NrOfCycles = int(self.NrCyclesEdt.text())
            globals.l_interval = int(self.IntervalEdt.text())
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
                globals.l_interval = int(self.IntervalEdt.text())
                self.logger = self.create_logger("log") ## initialise logger for timestamps
                self.recent_spectra_Abs = self.create_logger("allspectra_Abs")
                self.recent_spectra_Int = self.create_logger("allspectra_Int")
                self.save_recent_spectra()
                
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
        return ret

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
            time.sleep(self.delay_acq)
        if globals.AcquisitionMode != "Continuous":
            self.Shutter_Close()
        print("One Measurement done")
        globals.m_Cycle += 1
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
        The delay used for the loop is the user-defined interval subtracted by 
        the total sum of the delays due to the shutter and LED functionalities,
        such that the measurement of spectra is separated by approximately the user-defined interval.
        '''
        print("=== IrradiationKinetics_Measurement ===")
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(True)
        nummeas = globals.l_NrOfCycles + 1 ## nr of measurements (1 more than nr of cycles)
        delay_float = globals.l_interval - globals.delays_Shutter_plus_LED
        delay = int(delay_float) ## user-defined interval subtracted by total sum of delays
        self.cancelled = False

        print(f"delay_float: {delay_float}")
        print(f"===nummeas: {nummeas}\n===LED {self.selected_LED}, {self.current} mA ({self.percentage} %)")

        for i in range(nummeas):
            if self.cancelled == True: ## break loop if Stop button was pressed
                print("Cancelled IrradiationKinetics Measurement")
                self.turnLED_OFF()
                self.Shutter_Close()
                break
            else:
                print(f"i: {i}")
                self.One_Measurement() ## do one measurement
                if globals.m_Measurements != nummeas:
                    self.turnLED_ON() ## wait for a bit, and turn on LED
                    print(f"Waiting for {delay} s")
                    for t in range(delay):
                        time.sleep(1)
                        if self.cancelled == True:
                            break
                    if self.cancelled == False:
                        print(f"Delay {delay} s done")
                        self.turnLED_OFF() ## turn off LED, and wait for a bit
        
        if self.cancelled == False:
            print(f"Irradiation Kinetics measurement done ({nummeas} measurements)")
        if self.ChkAutoSaveFolder.isChecked():
            self.log_autoQY = self.create_logger("log_for_autoQY")
            DataHandling.ConvertTimestamps(self.logger.filename, self.log_autoQY.filename) ## generate log file meant for autoQY: timestamps of actual irradiation times
        
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        return

    @pyqtSlot()
    def on_StopMeasBtn_clicked(self): 
        print("=== StopMeasBtn clicked ===")
        self.cancel.emit() ## connected to cancel_meas(self)
        time.sleep(1)
        self.StartMeasBtn.setEnabled(True)
        self.StopMeasBtn.setEnabled(False)
        return

    @pyqtSlot()
    def cancel_meas(self):
        ret = ava.AVS_StopMeasure(globals.dev_handle)
        self.cancelled = True
        return ret

    @pyqtSlot()
    def on_AutoSaveFolderBtn_clicked(self):
        folder = QFileDialog.getExistingDirectory(self,
                                                  "Choose folder for auto-saving", 
                                                  "",
                                                  QFileDialog.ShowDirsOnly)
        if folder:
            globals.AutoSaveFolder = folder
        else:
            print("No auto-save folder selected.")
            globals.AutoSavefolder = Settings.Default_AutoSaveFolder
            ##!!! PRINT MESSAGE: NO AUTO-SAVE FOLDER SELECTED: REVERTED TO BACK-UP
                ## CREATE BACK-UP FOLDER WITH NAME: DATE AND TIME
        
        self.update_label_AutoSaveFolder()
        return

    def update_label_AutoSaveFolder(self):
        self.Label_AutoSaveFolder.setText(globals.AutoSaveFolder)
        print(f"Auto-Save Folder: {globals.AutoSaveFolder}")

    ###########################################################################
    ###########################################################################

##!!! TEST AND FIND OPTIMAL DELAY TIME (see DefaultSettings)
    def Shutter_Open(self):
        ava.AVS_SetDigOut(globals.dev_handle, ava.PortID_Internal_LightSource, ava.SHUTTER_OPEN) ## open shutter
        self.record_event("Open_Shutter") ## add timestamp to log file
        time.sleep(self.delay_afterShutter_Open) ## short delay between Open Shutter and Measure

    def Shutter_Close(self):
        time.sleep(self.delay_beforeShutter_Close) ## short delay between Measure and Close Shutter
        ava.AVS_SetDigOut(globals.dev_handle, ava.PortID_Internal_LightSource, ava.SHUTTER_CLOSE) ## close shutter
        self.record_event("Close_Shutter") ## add timestamp to log file
        time.sleep(self.delay_afterShutter_Close) ## short delay after Close Shutter

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
            self.SpectrometerList.setItem(0, 3, QTableWidgetItem(f"{Settings.LED_initialisation}")) 
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
        self.update_label_CurrentLED()

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
        if not (self.StartMeasBtn.isEnabled()): ## if on-going measurement
            time.sleep(self.delay_beforeLED_ON) ## delay after measurement (Shutter_Close)
        LEDControl.turnLED_ON()
        self.record_event("LED_ON") ## add timestamp to log file
        self.update_label_LEDstatus()

    def turnLED_OFF(self):
        LEDControl.turnLED_OFF()
        self.record_event("LED_OFF") ## add timestamp to log file
        self.update_label_LEDstatus()
        if not (self.StartMeasBtn.isEnabled()): ## if on-going measurement
            time.sleep(self.delay_afterLED_OFF) ## delay before measurement (Shutter_Open)

    ###########################################################################
    ###########################################################################
    @pyqtSlot()
    def update_plot(self):
        if (self.DisableGraphChk.isChecked() == False):
            if (self.ScopeModeBtn.isChecked()):
                if globals.MeasurementType == "Dark":
                    self.plot_monitor.update_plot(globals.DarkSpectrum)
                elif globals.MeasurementType == "Ref":
                    self.plot_monitor.update_plot(globals.RefSpectrum_DarkSLSCorr) ## plot.py/update_plot
                elif globals.MeasurementType == "Measurement":
                    self.plot_monitor.update_plot(globals.ScopeSpectrum_DarkSLSCorr)
            elif (self.AbsorbanceModeBtn.isChecked()):
                self.plot_monitor.update_absorbanceplot()
            else:
                QMessageBox.warning(self, "Error", "Something wrong with Measurement Mode")                
        
        #######################################################################
        
        if (self.PlotMeasuredSpectraChk.isChecked() == True):
            if (self.ScopeModeBtn.isChecked()):
                if globals.AcquisitionMode in ("Kin", "IrrKin"):
                    dataframe = self.recent_spectra_Int.load_df_spectra()
                    self.plot_spectra.recent_spectra(dataframe)
            elif (self.AbsorbanceModeBtn.isChecked()):
                if globals.AcquisitionMode in ("Kin", "IrrKin"):
                    dataframe = self.recent_spectra_Abs.load_df_spectra()
                    self.plot_spectra.recent_spectra(dataframe)
            else:
                # QMessageBox.warning(self, "Error", "Something wrong with Measurement Mode")
                print("Something wrong with Measurement Mode")
        
        #######################################################################
        
        if (self.PlotTraceChk.isChecked()):
            if self.TraceWavelengthChk_1.isChecked() or self.TraceWavelengthChk_2.isChecked():
                if self.TraceWavelengthChk_1.isChecked():
                    globals.TraceWavelength_1 = int(self.TraceWavelength_1.text())
                if self.TraceWavelengthChk_2.isChecked():
                    globals.TraceWavelength_2 = int(self.TraceWavelength_2.text())
                    ##!!! ADD OPTION FOR 2 OR 3 TRACE WAVELENGTHS
            
                if (self.ScopeModeBtn.isChecked()):
                    if globals.AcquisitionMode in ("Kin", "IrrKin"):
                        dataframe = self.recent_spectra_Int.load_df_spectra()
                        index_1, wavelength_1 = self.recent_spectra_Int.trace_wavelength(globals.TraceWavelength_1)
                        self.plot_trace.trace(globals.m_Measurements, dataframe, index_1, wavelength_1)
                elif (self.AbsorbanceModeBtn.isChecked()):
                    if globals.AcquisitionMode in ("Kin", "IrrKin"):
                        dataframe = self.recent_spectra_Abs.load_df_spectra()
                        index_1, wavelength_1 = self.recent_spectra_Abs.trace_wavelength(globals.TraceWavelength_1)
                        self.plot_trace.trace(globals.m_Measurements, dataframe, index_1, wavelength_1)
            else:
                pass
            
        return

    def create_logger(self, name):
        if self.ChkAutoSaveFolder.isChecked():
            logger = DataHandling.Logger(f"{globals.AutoSaveFolder}/{name}.csv", "log") ## initialise logger for timestamps
        return logger
    
    def save_recent_spectra(self):
        if self.ChkAutoSaveFolder.isChecked():
            self.recent_spectra_Abs.save_wavelengths(globals.wavelength)
            self.recent_spectra_Int.save_wavelengths(globals.wavelength)

    def record_event(self, event_name):
        if self.ChkAutoSaveFolder.isChecked():
            if globals.AcquisitionMode in ("Kin", "IrrKin"):
                print(f"Event: {event_name}")
                self.logger.log(event_name)
        else:
            # print("Auto-Saving turned off")
            pass

    @pyqtSlot()
    def auto_save(self, foldername, mode, spectrum, data_header):
        '''
        Saves spectrum as .csv file
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
        if globals.AcquisitionMode in ("Kin", "IrrKin"):
            ##!!! CHANGE MEASUREMENT NR TO: 0001, 0002, ..., 0118, etc.
            filepath = f"{foldername}/{mode}_{globals.m_Measurements}.csv"
        else:
            filepath = f"{foldername}/{mode}.csv"
        
        if self.ChkAutoSaveFolder.isChecked() or mode in ("Dark", "Ref"):
            file = DataHandling.Logger(filepath, "spectra") ## initialise logger for spectrum savefile
            file.save_spectrum(globals.wavelength, spectrum, data_header)
            self.statusBar.showMessage(f"{mode} Spectrum auto-saved as {file}")
        else:
            print("Auto-Saving turned off")


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
                        globals.m_Measurements += 1
                        self.record_event("Measurement")
                        
                        timestamp = 0 ##!!! ADJUST to use for how long acquisition took
                        timestamp, globals.spectraldata = ava.AVS_GetScopeData(globals.dev_handle) ## globals.spectraldata is array of doubles
                        ##################
                        savefolder = globals.AutoSaveFolder
                        ##################
                        if globals.MeasurementType == "Dark":
                            globals.DarkSpectrum_doublearray = globals.spectraldata
                            globals.DarkSpectrum = globals.DarkSpectrum_doublearray[:globals.pixels]
                            self.auto_save(savefolder, "Dark", globals.DarkSpectrum, "Intensity")
                        elif globals.MeasurementType == "Ref":
                            globals.RefSpectrum_doublearray = globals.spectraldata
                            globals.RefSpectrum = globals.RefSpectrum_doublearray[:globals.pixels]
                            self.auto_save(savefolder, "Ref", globals.RefSpectrum, "Intensity")
                            
                            #### Dark-Corrected ####
                            globals.RefSpectrum_DarkCorr = [globals.RefSpectrum_doublearray[x] - globals.DarkSpectrum_doublearray[x] for x in range(globals.pixels)]
                            self.auto_save(savefolder, "Ref_DarkCorr", globals.RefSpectrum_DarkCorr, "Intensity (Dark-Corrected)")
                            
                            #####################################
                            if self.SLSCorrCheck.isChecked():
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
                                self.auto_save(savefolder, "Ref_DarkSLSCorr", globals.RefSpectrum_DarkSLSCorr, "Intensity (Dark- and SLS-Corrected)")
                            
                            ##!!! SAVE ALL REFERENCE SPECTRA IN ONE FILE

                        elif globals.MeasurementType == "Measurement":
                            globals.ScopeSpectrum_doublearray = globals.spectraldata
                            globals.ScopeSpectrum = globals.ScopeSpectrum_doublearray[:globals.pixels]
                            
                            #### Dark Correction ####
                            globals.ScopeSpectrum_DarkCorr = [globals.ScopeSpectrum_doublearray[x] - globals.DarkSpectrum_doublearray[x] for x in range(globals.pixels)]

                            self.auto_save(savefolder, f"{globals.AcquisitionMode}_Int", globals.ScopeSpectrum, "Intensity")
                            self.auto_save(savefolder, f"{globals.AcquisitionMode}_Int_DarkCorr", globals.ScopeSpectrum_DarkCorr, "Intensity (Dark-Corrected)")
                            
                            #####################################
                            ############### SLS #################
                            #####################################
                            if self.SLSCorrCheck.isChecked():
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
                                
                                self.auto_save(savefolder, f"{globals.AcquisitionMode}_Int_DarkSLSCorr", globals.ScopeSpectrum_DarkSLSCorr, "Intensity (Dark- and SLS-Corrected)")
                        
                            #####################################
                            ########## ABSORBANCE MODE ##########
                            #####################################
                            if (self.AbsorbanceModeBtn.isChecked()): ## Absorbance mode
                                if self.SLSCorrCheck.isChecked():
                                    globals.AbsSpectrum_doublearray = [log10(globals.RefSpectrum_DarkSLSCorr_doublearray[x] / globals.ScopeSpectrum_DarkSLSCorr_doublearray[x]) if globals.ScopeSpectrum_DarkSLSCorr_doublearray[x]>0 and globals.RefSpectrum_DarkSLSCorr_doublearray[x]>0 else 0.0 for x in range(globals.pixels)]
                                    globals.AbsSpectrum = list(globals.AbsSpectrum_doublearray)
                                    self.auto_save(savefolder, f"{globals.AcquisitionMode}_Abs", globals.AbsSpectrum, "Absorbance")
                                else:
                                    globals.AbsSpectrum_doublearray = [log10(globals.RefSpectrum_DarkCorr_doublearray[x] / globals.ScopeSpectrum_DarkSLSCorr_doublearray[x]) if globals.ScopeSpectrum_DarkSLSCorr_doublearray[x]>0 and globals.RefSpectrum_DarkSLSCorr_doublearray[x]>0 else 0.0 for x in range(globals.pixels)]
                                    globals.AbsSpectrum = list(globals.AbsSpectrum_doublearray)
                                    self.auto_save(savefolder, f"{globals.AcquisitionMode}_Abs_noSLS", globals.AbsSpectrum, "Absorbance (No SLS Correction)")

                            #####################################
                            ########## SAVE IN ONE FILE ##########
                            #####################################
                            if globals.AcquisitionMode in ("Kin", "IrrKin"):
                                if (self.AbsorbanceModeBtn.isChecked()): ## Absorbance mode
                                    self.recent_spectra_Abs.build_df_spectra(globals.AbsSpectrum, globals.m_Measurements)
                                elif (self.ScopeModeBtn.isChecked()):
                                    self.recent_spectra_Int.build_df_spectra(globals.ScopeSpectrum_DarkSLSCorr, globals.m_Measurements)

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
                        
                        #######################################################
                        ##!!! SHOULD BE TIME PER ACQUISITION: TRY AND CHANGE IT
                        l_Dif = timestamp - globals.m_PreviousTimeStamp  # timestamps in 10 us ticks
                        globals.m_PreviousTimeStamp = timestamp ##!!! use this as timestamp
                        
                        if (globals.m_Measurements > 1):
                            globals.m_SummatedTimeStamps += l_Dif
                            self.label_LastScan.setText("{0:.3f}".format(l_Dif/100.0))  # in millisec
                            timeperscan = float(globals.m_SummatedTimeStamps) / float(100.0 * (globals.m_Measurements - 1))
                            self.label_TimePerScan.setText("{0:.3f}".format(timeperscan))
                        else:
                            self.label_LastScan.setText("")
                            self.label_TimePerScan.setText("")
                        #######################################################

                        l_MilliSeconds = globals.m_DateTime_start.msecsTo(QDateTime.currentDateTime()) ## difference in milliseconds between current and start time
                        l_Seconds = l_MilliSeconds/1000
                        print(f"handle_newdata timestamp: {l_Seconds} (s)")
                        
                        self.label_TimeSinceStart.setText(f"{l_Seconds:.3f}")
                        self.label_CurrentCycleNr.setText(f"{globals.m_Cycle}")
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
        self.label_NrFailures.setText("{0:d}".format(globals.m_Failures))    
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
        self.IntTimeEdt.setText("{0:.1f}".format(l_DeviceData.m_StandAlone_m_Meas_m_IntegrationTime)) ## sets integration time to EEPROM default
        l_FPGAClkCycles = l_DeviceData.m_StandAlone_m_Meas_m_IntegrationDelay
        l_NanoSec = 125.0*(l_FPGAClkCycles-1.0)/6.0
        
        l_DeviceData.m_StandAlone_m_Meas_m_NrAverages = 10
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
        Function is activated upon activating the connection with the spectrometer,
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
        elif (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_TCD1304):    
            self.PreScanChk.show()    
            self.PreScanChk.setCheckState(Qt.Checked)
            l_Res = ava.AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked()) 
        elif (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU256LSB):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(False)
            self.HighSensitivityRBtn.setChecked(True)  # High Sensitive default for SU256LSB
            l_Res = ava.AVS_SetSensitivityMode(globals.dev_handle, 1)
        elif (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_SU512LDB):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(False)
            self.HighSensitivityRBtn.setChecked(True)  # High Sensitive default for SU512LDB
            l_Res = ava.AVS_SetSensitivityMode(globals.dev_handle, 1) 
        elif (globals.DeviceData.m_Detector_m_SensorType == ava.SENS_HAMG9208_512):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(True)  # low noise default
            self.HighSensitivityRBtn.setChecked(False)
            l_Res = ava.AVS_SetSensitivityMode(globals.dev_handle, 0)
        else: 
            l_Res = None

        ret = ava.AVS_UseHighResAdc(globals.dev_handle, True)
        ret = ava.AVS_EnableLogging(False)
            
        globals.pixels = globals.DeviceData.m_Detector_m_NrPixels
        self.NrPixelsEdt.setText("{0:d}".format(globals.pixels))
        globals.startpixel = globals.DeviceData.m_StandAlone_m_Meas_m_StartPixel
        globals.stoppixel = globals.DeviceData.m_StandAlone_m_Meas_m_StopPixel
        globals.wavelength_doublearray = ava.AVS_GetLambda(globals.dev_handle) ## wavelength data here
        globals.wavelength = globals.wavelength_doublearray[:globals.pixels]
        self.reset_RefDark()
        return l_Res, ret

    def DefaultSettings(self):
        '''
        ava.MeasConfigType() contains specific configuration and gets used with ret = AVS_PrepareMeasure
        '''
        self.measconfig.m_StartPixel = globals.startpixel
        self.measconfig.m_StopPixel = globals.stoppixel
        
        l_NanoSec = float(self.IntDelayEdt.text())
        self.measconfig.m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0) ## from Avantes
        self.measconfig.m_IntegrationTime = 3 # default integration time (ms)
        self.IntTimeEdt.setText(f"{self.measconfig.m_IntegrationTime:0.1f}") 
        
        self.measconfig.m_NrAverages = 100
        self.AvgEdt.setText(f"{self.measconfig.m_NrAverages:0d}") ## default # averages
        
        self.delay_acq = (self.measconfig.m_IntegrationTime * self.measconfig.m_NrAverages)/1000 # acquisition time (s)
        
        self.delay_afterShutter_Open = 0.5 # seconds
        self.delay_beforeShutter_Close = 0.1 # seconds
        self.delay_afterShutter_Close = 0.1 # seconds
        
        globals.delays_aroundShutter = self.delay_afterShutter_Open + self.delay_afterShutter_Close
        globals.delays_Shutter_plus_LED = globals.delays_aroundShutter + globals.delays_aroundLED
        
        ##!!! move setting of measconfig parameters to Activate function (probably)
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
        self.SLSCorrCheck.setChecked(True) ## Stray Light Suppression/Correction

        #######################################################################        
        self.measconfig.m_SaturationDetection = 1
        if self.measconfig.m_SaturationDetection == 1:
            self.SatDetEdt.setText("on")
        elif self.measconfig.m_SaturationDetection == 0:
            self.SatDetEdt.setText("off")
        self.measconfig.m_Trigger_m_Mode = 0
        self.InternalTriggerBtn.setChecked(True)
        
        self.NrCyclesEdt.setText("10") ## default nr. measurements
        self.IntervalEdt.setText("10") # default interval in seconds
        
        globals.AutoSaveFolder = Settings.Default_AutoSaveFolder
        self.update_label_AutoSaveFolder()
        self.PrintSettings()
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
    
    def update_label_CurrentLED(self):
        self.Label_CurrentLED.setText(str(self.selected_LED))
    
    def update_label_LEDstatus(self):
        self.LED_DisplayStatus.setText(Settings.LEDstatus)

    ###########################################################################
    ###########################################################################
    ###########################################################################
    
    def handle_radio_selection(self):
        ''' Radiobutton selection influences available additional settings '''
        if self.SingleRBtn.isChecked():
            self.NrCyclesEdt.setEnabled(False)
            self.label_NrCyclesEdt.setEnabled(False)
            self.IntervalEdt.setEnabled(False)
            self.label_IntervalEdt.setEnabled(False)
        if self.ContinuousRBtn.isChecked():
            self.NrCyclesEdt.setEnabled(True)
            self.label_NrCyclesEdt.setEnabled(True)
            self.IntervalEdt.setEnabled(False)
            self.label_IntervalEdt.setEnabled(False)
        if self.KineticsRBtn.isChecked():
            self.NrCyclesEdt.setEnabled(True)
            self.label_NrCyclesEdt.setEnabled(True)
            self.IntervalEdt.setEnabled(True)
            self.label_IntervalEdt.setEnabled(True)
        if self.IrrKinRBtn.isChecked():
            self.NrCyclesEdt.setEnabled(True)
            self.label_NrCyclesEdt.setEnabled(True)
            self.IntervalEdt.setEnabled(True)
            self.label_IntervalEdt.setEnabled(True)
        
        if self.ScopeModeBtn.isChecked():
            globals.MeasurementMode = "Int"
        if self.AbsorbanceModeBtn.isChecked():
            globals.MeasurementMode = "Abs"
            
        if (self.PlotTraceChk.isChecked() == False):
            self.TraceWavelengthChk_1.setEnabled(False)
            self.TraceWavelengthChk_2.setEnabled(False)
        if (self.PlotTraceChk.isChecked() == True):
            self.TraceWavelengthChk_1.setEnabled(True)
            self.TraceWavelengthChk_2.setEnabled(True)
        
        if (self.TraceWavelengthChk_1.isChecked() == False):
            self.label_Trace_1.setEnabled(False)
            self.TraceWavelength_1.setEnabled(False)
        if self.TraceWavelengthChk_1.isChecked():
            self.label_Trace_1.setEnabled(True)
            self.TraceWavelength_1.setEnabled(True)
        if (self.TraceWavelengthChk_2.isChecked() == False):
            self.label_Trace_2.setEnabled(False)
            self.TraceWavelength_2.setEnabled(False)
        if self.TraceWavelengthChk_2.isChecked():
            self.label_Trace_2.setEnabled(True)
            self.TraceWavelength_2.setEnabled(True)
        
    def handle_textfield_change(self):
        ##!!! SHOULD BE A FLOAT (to allow, e.g., 3.5 ms)
        if float(self.IntTimeEdt.text()) != self.measconfig.m_IntegrationTime:
            self.StatusLabel_Settings.setText("Settings NOT saved!")
        if int(self.AvgEdt.text()) != self.measconfig.m_NrAverages:
            self.StatusLabel_Settings.setText("Settings NOT saved!")
    
    def reset_RefDark(self):
        self.StatusLabel_Dark.setText("") ## show empty
        self.StatusLabel_Ref.setText("") ## show empty
        self.StatusLabel_Ref.setEnabled(False)
        self.RefMeasBtn.setEnabled(False)
        self.DarkMeasBtn.setEnabled(True)
        self.ScopeModeBtn.setChecked(True)
        self.AbsorbanceModeBtn.setEnabled(False)
        print(f"globals.MeasurementMode: {globals.MeasurementMode}")
    
    def PrintSettings(self):
        print(f"self.measconfig.m_IntegrationTime: {self.measconfig.m_IntegrationTime}")
        print(f"self.delay_acq: {self.delay_acq} s")
        print(f"self.delay_afterShutter_Open: {self.delay_afterShutter_Open} s")
        print(f"self.delay_beforeShutter_Close: {self.delay_beforeShutter_Close} s")
        print(f"self.delay_afterShutter_Close: {self.delay_afterShutter_Close} s")
    
    ###########################################################################
    ###########################################################################
    ###########################################################################
    
    @pyqtSlot()
    def on_DeactivateBtn_clicked(self):
        ret = ava.AVS_Deactivate(globals.dev_handle)
        globals.dev_handle = ava.INVALID_AVS_HANDLE_VALUE
        self.on_UpdateListBtn_clicked()
        self.DisconnectGui()
        return ret

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
