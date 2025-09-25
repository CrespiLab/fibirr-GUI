#!/usr/bin/env python3
from ast import Str
from inspect import ArgSpec
import os
import platform
import sys
import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from avaspec import *
import globals
import qtdemo
import analog_io_demo
import digital_io_demo
import eeprom_demo

class QtdemoClass(QMainWindow, qtdemo.Ui_QtdemoClass):
    timer = QTimer() 
    SPECTR_LIST_COLUMN_COUNT = 5
    newdata = pyqtSignal(int, int)
    dstrStatus = pyqtSignal(int, int)

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.PreScanChk.hide()
        self.SetNirSensitivityRgrp.hide()
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
        self.ShowEepromBtn.setEnabled(False)
        self.ReadEepromBtn.setEnabled(False)
        self.WriteEepromBtn.setEnabled(False)        
        self.StartMeasBtn.setEnabled(False)
        self.StopMeasBtn.setEnabled(False)
        self.ResetSpectrometerBtn.setEnabled(False)        
        self.ConnectUSBRBtn.setChecked(True)
        self.ConnectEthernetRBtn.setChecked(False)
        self.FixedNrRBtn.setChecked(True)
        self.ContinuousRBtn.setChecked(False)
        self.RepetitiveRBtn.setChecked(False)
        self.DstrStatusUpdateBtn.setEnabled(False)
        self.DstrProgBar.setRange(0, 1)
        self.DstrProgBar.setValue(0)
        self.DssEvent_Chk.setChecked(False)
        self.FoeEvent_Chk.setChecked(False)
        self.IErrorEvent_Chk.setChecked(False)
        self.SpectrometerList.clicked.connect(self.on_SpectrometerList_clicked)
#       self.OpenCommBtn.clicked.connect(self.on_OpenCommBtn_clicked)
#       for buttons, do not use explicit connect together with the on_ notation, or you will get
#       two signals instead of one!
        self.timer.timeout.connect(self.update_plot)
        self.timer.stop()
        self.newdata.connect(self.handle_newdata)
        self.dstrStatus.connect(self.handle_dstrstatus)
        self.DisableGraphChk.stateChanged.connect(self.on_DisableGraphChk_stateChanged)
        AVS_Done()

    def measure_cb(self, pparam1, pparam2):
        param1 = pparam1[0] # dereference the pointers
        param2 = pparam2[0]
        self.newdata.emit(param1, param2)

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
        l_Ret = AVS_Init(la_Port)    
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
                if (l_Ret == ERR_ETHCONN_REUSE):
                    # A list of spectrometers can still be provided by the DLL
                    self.statusBar.showMessage("Server error; another instance is running!")
                    self.on_UpdateListBtn_clicked()
                else:
                    self.statusBar.showMessage("Server error; open communication failed with AVS_Init() error: {0:d}".format(l_Ret))
            AVS_Done()
            # QMessageBox.critical(self,"Error","No devices were found!") 
        return

    @pyqtSlot()
    def on_CloseCommBtn_clicked(self):
        # First make sure that there is no measurement running, AVS_Done() must be called when 
        # there is no measurement running!
        if (globals.dev_handle != INVALID_AVS_HANDLE_VALUE):
            AVS_StopMeasure(globals.dev_handle)
            AVS_Deactivate(globals.dev_handle) 
            globals.dev_handle = INVALID_AVS_HANDLE_VALUE
        AVS_Done()
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
            lUsbDevListSize = AVS_UpdateUSBDevices()
            l_pId = AvsIdentityType * lUsbDevListSize
            l_pId = AVS_GetList(lUsbDevListSize)
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
            l_pEth = AVS_UpdateETHDevices(1)
            lEthListSize = len(l_pEth)
            l_pId = AvsIdentityType * lEthListSize
            l_pId = AVS_GetList(lEthListSize)
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
            l_Id = AvsIdentityType * 1
            l_Items = QListWidget()
            l_Items = self.SpectrometerList.selectedItems()
            l_Text = l_Items[0].text()
            l_Id.SerialNumber = l_Text.encode('utf-8')
            l_Id.UserFriendlyName = b"\x00"
            l_Id.Status = b"\x01"
            globals.dev_handle = AVS_Activate(l_Id)
            if (INVALID_AVS_HANDLE_VALUE == globals.dev_handle):
                QMessageBox.critical(self, "Qt Demo", "Error opening device {}".format(l_Text))
            else:
                m_Identity = l_Id
                globals.mSelectedDevRow = self.SpectrometerList.currentItem().row()
                self.on_UpdateListBtn_clicked()
                self.ConnectGui()
                self.on_ReadEepromBtn_clicked()
                dtype = 0
                dtype = AVS_GetDeviceType(globals.dev_handle)  
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
                self.DstrRBtn.setEnabled(dtype == 3)  # only available on AS7010
        return

    @pyqtSlot()
    def on_StartMeasBtn_clicked(self):
        ret = AVS_UseHighResAdc(globals.dev_handle, True)
        ret = AVS_EnableLogging(False)
        measconfig = MeasConfigType()
        measconfig.m_StartPixel = int(self.StartPixelEdt.text())
        measconfig.m_StopPixel = int(self.StopPixelEdt.text())
        measconfig.m_IntegrationTime = float(self.IntTimeEdt.text())
        l_NanoSec =  float(self.IntDelayEdt.text())
        measconfig.m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0)
        measconfig.m_NrAverages = int(self.AvgEdt.text())
        measconfig.m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked()
        measconfig.m_CorDynDark_m_ForgetPercentage = int(self.DarkCorrPercEdt.text())
        measconfig.m_Smoothing_m_SmoothPix = int(self.SmoothNrPixelsEdt.text())
        measconfig.m_Smoothing_m_SmoothModel = int(self.SmoothModelEdt.text())
        measconfig.m_SaturationDetection = int(self.SatDetEdt.text())
        if (self.SoftwareTriggerRBtn.isChecked()):
            measconfig.m_Trigger_m_Mode = 0
        if (self.HardwareTriggerRBtn.isChecked()):
            measconfig.m_Trigger_m_Mode = 1
        if (self.SingleScanTriggerRBtn.isChecked()):
            measconfig.m_Trigger_m_Mode = 2                
        measconfig.m_Trigger_m_Source =  self.SynchTriggerRBtn.isChecked()
        measconfig.m_Trigger_m_SourceType = self.LevelTriggerRBtn.isChecked()
        measconfig.m_Control_m_StrobeControl = int(self.FlashesPerScanEdt.text())
        l_NanoSec = float(self.LaserDelayEdt.text())        
        measconfig.m_Control_m_LaserDelay = int(6.0*l_NanoSec/125.0)
        l_NanoSec = float(self.LaserWidthEdt.text())
        measconfig.m_Control_m_LaserWidth = int(6.0*l_NanoSec/125.0)
        measconfig.m_Control_m_LaserWaveLength = float(self.LaserWavEdt.text())
        if (self.StoreToRamRBtn.isChecked() or self.DstrRBtn.isChecked()):
            measconfig.m_Control_m_StoreToRam = int(self.NrStoreToRamEdt.text())
        else:    
            measconfig.m_Control_m_StoreToRam = 0
        ret = AVS_PrepareMeasure(globals.dev_handle, measconfig)
        if (globals.DeviceData.m_Detector_m_SensorType == SENS_TCD1304):
            AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked())
        if ((globals.DeviceData.m_Detector_m_SensorType == SENS_HAMS9201) or 
            (globals.DeviceData.m_Detector_m_SensorType == SENS_SU256LSB) or
            (globals.DeviceData.m_Detector_m_SensorType == SENS_SU512LDB)):
            AVS_SetSensitivityMode(globals.dev_handle, self.HighSensitivityRBtn.isChecked())
        if (self.FixedNrRBtn.isChecked()):
            l_NrOfScans = int(self.NrMeasEdt.text())
        if (self.ContinuousRBtn.isChecked()):
            l_NrOfScans = -1
        if (self.RepetitiveRBtn.isChecked()):
             l_NrOfScans = int(self.NrMeasEdt.text())
        if (self.StoreToRamRBtn.isChecked()):
            l_NrOfScans = 1
        if (self.DstrRBtn.isChecked()):
            l_NrOfScans = -2
            dynstr_cb = AVS_DstrCallbackFunc(self.dstr_cb)
            l_Res = AVS_SetDstrStatusCallback(globals.dev_handle, dynstr_cb)
        if (self.StartMeasBtn.isEnabled()):
            globals.m_DateTime_start = QDateTime.currentDateTime()
            globals.m_SummatedTimeStamps = 0.0
            globals.m_Measurements = 0
            globals.m_Failures = 0
            self.TimeSinceStartEdt.setText("{0:d}".format(0))
            self.NrScansEdt.setText("{0:d}".format(0))
            self.NrFailuresEdt.setText("{0:d}".format(0))
        self.StartMeasBtn.setEnabled(False) 
        self.timer.start(200)   
        globals.startpixel = measconfig.m_StartPixel
        globals.stoppixel = measconfig.m_StopPixel
        if (self.RepetitiveRBtn.isChecked()):
            lmeas = 0
            while (self.StartMeasBtn.isEnabled() == False):
                avs_cb = AVS_MeasureCallbackFunc(self.measure_cb)
                l_Res = AVS_MeasureCallback(globals.dev_handle, avs_cb, 1)
                while (globals.m_Measurements - lmeas) < 1: 
                    time.sleep(0.001)
                    qApp.processEvents()
                lmeas += 1
        else:    
            avs_cb = AVS_MeasureCallbackFunc(self.measure_cb)
            l_Res = AVS_MeasureCallback(globals.dev_handle, avs_cb, l_NrOfScans)
            if (0 != l_Res):
                self.statusBar.showMessage("AVS_MeasureCallback failed, error: {0:d}".format(l_Res))    
            else:
                globals.mDstrRecvCount = 0
                self.DstrStatusRecvCountEdt.setText("{0:d}".format(globals.mDstrRecvCount))
                if (self.DstrRBtn.isChecked() == False):
                    # Reset all fields that have nothing to do with DSTR
                    self.DstrTotalScansEdt.setText("")
                    self.DstrUsedScansEdt.setText("")
                    self.DstrFlagsEdt.setText("")
                    self.DstrProgBar.setValue(0)
                    self.DssEvent_Chk.setChecked(False)
                    self.FoeEvent_Chk.setChecked(False)
                    self.IErrorEvent_Chk.setChecked(False)
                    self.statusBar.showMessage("Meas.Status: pending")
                if (self.FixedNrRBtn.isChecked()):
                    while globals.m_Measurements <= l_NrOfScans:
                        time.sleep(0.001)
                        qApp.processEvents()
                else:        
                    if (self.ContinuousRBtn.isChecked() or
                        self.StoreToRamRBtn.isChecked() or
                        self.DstrRBtn.isChecked()):
                        while True: 
                            time.sleep(0.001)
                            qApp.processEvents()
        return

    @pyqtSlot()
    def on_StopMeasBtn_clicked(self): 
        ret = AVS_StopMeasure(globals.dev_handle)
        self.StartMeasBtn.setEnabled(True)
        self.timer.stop()
        return

    @pyqtSlot()
    def update_plot(self):
        if (self.DisableGraphChk.isChecked() == False):
            self.plot.update_plot()
        if (globals.m_Measurements == int(self.NrMeasEdt.text())):
            self.StartMeasBtn.setEnabled(True)    
        return         

    @pyqtSlot(int, int)
    def handle_newdata(self, ldev_handle, lerror):
        if (lerror >= 0):
            if ((ldev_handle == globals.dev_handle) and (globals.pixels > 0)):
                if (lerror == 0): # normal measurements
                    self.statusBar.showMessage("Meas.Status: success")
                    timestamp = 0
                    globals.m_Measurements += 1
                    timestamp, globals.spectraldata = AVS_GetScopeData(globals.dev_handle)
                    globals.saturated = AVS_GetSaturatedPixels(globals.dev_handle)
                    SpectrumIsSatured = False
                    j = 0
                    while j < (globals.stoppixel - globals.startpixel):
                        SpectrumIsSatured = SpectrumIsSatured or globals.saturated[j]
                        j += 1
                        self.SaturatedChk.setChecked(SpectrumIsSatured)
                    # self.plot.update_plot()
                    l_Dif = timestamp - globals.m_PreviousTimeStamp  # timestamps in 10 us ticks
                    globals.m_PreviousTimeStamp = timestamp
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
                    if (self.FixedNrRBtn.isChecked()):
                       self.StartMeasBtn.setEnabled(int(self.NrMeasEdt.text()) == globals.m_Measurements) 
                else: # StoreToRam measurements
                    l_AvgScantimeRAM = 0.0
                    self.statusBar.showMessage("Meas.Status: Reading RAM")
                    j = 0
                    while j < lerror:
                        timestamp, globals.spectraldata = AVS_GetScopeData(globals.dev_handle)
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

    @pyqtSlot(int, int)
    def handle_dstrstatus(self, ldev_handle, lstatus):
        if (ldev_handle == globals.dev_handle): 
            globals.mDstrRecvCount += 1
            self.on_DstrStatusUpdateBtn_clicked()
        if (lstatus > 0):
            self.StartMeasBtn.setEnabled(True)
        return

    @pyqtSlot()
    def on_DstrStatusUpdateBtn_clicked(self):
        l_DstrStatus = DstrStatusType()
        l_DstrStatus = AVS_GetDstrStatus(globals.dev_handle)
        if (self.DstrRBtn.isChecked() == True):
            self.DstrStatusRecvCountEdt.setText("{0:d}".format(globals.mDstrRecvCount))
            self.DstrTotalScansEdt.setText("{0:d}".format(l_DstrStatus.m_TotalScans))
            self.DstrUsedScansEdt.setText("{0:d}".format(l_DstrStatus.m_UsedScans))
            self.DstrFlagsEdt.setText("{0:08b}".format(l_DstrStatus.m_Flags))
            self.DssEvent_Chk.setChecked(l_DstrStatus.m_Flags & DSTR_STATUS_DSS_MASK)
            self.FoeEvent_Chk.setChecked(l_DstrStatus.m_Flags & DSTR_STATUS_FOE_MASK)
            self.IErrorEvent_Chk.setChecked(l_DstrStatus.m_Flags & DSTR_STATUS_IERR_MASK) 
            if (l_DstrStatus.m_TotalScans > 0):
                self.DstrProgBar.setRange(0, l_DstrStatus.m_TotalScans)
                self.DstrProgBar.setValue(l_DstrStatus.m_UsedScans)      
        return    

    @pyqtSlot()
    def on_ReadEepromBtn_clicked(self):
        l_DeviceData = DeviceConfigType()
        l_DeviceData = AVS_GetParameter(globals.dev_handle, 63484)
        # show measurement settings
        self.StartPixelEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_StartPixel))
        self.StopPixelEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_StopPixel))
        self.IntTimeEdt.setText("{0:.3f}".format(l_DeviceData.m_StandAlone_m_Meas_m_IntegrationTime))
        l_FPGAClkCycles = l_DeviceData.m_StandAlone_m_Meas_m_IntegrationDelay
        l_NanoSec = 125.0*(l_FPGAClkCycles-1.0)/6.0
        self.IntDelayEdt.setText("{0:.0f}".format(l_NanoSec))
        self.AvgEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_NrAverages))
        self.SatDetEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_SaturationDetection))
        self.SoftwareTriggerRBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 0)
        self.HardwareTriggerRBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 1)
        self.SingleScanTriggerRBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 2)
        self.ExternalTriggerRbtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source == 0)
        self.SynchTriggerRBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source == 1)
        self.EdgeTriggerRBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType == 0)
        self.LevelTriggerRBtn.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType == 1)
        self.DarkCorrChk.setChecked(l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable == 1)
        self.DarkCorrPercEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage))
        self.SmoothModelEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel))
        self.SmoothNrPixelsEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix))
        self.FlashesPerScanEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_Control_m_StrobeControl))
        l_FPGAClkCycles = l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserDelay
        l_NanoSec = 125.0*(l_FPGAClkCycles)/6.0
        self.LaserDelayEdt.setText("{0:.0f}".format(l_NanoSec))
        l_FPGAClkCycles = l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWidth
        l_NanoSec = 125.0*(l_FPGAClkCycles)/6.0
        self.LaserWidthEdt.setText("{0:.0f}".format(l_NanoSec))
        self.LaserWavEdt.setText("{0:.3f}".format(l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWaveLength))
        self.NrStoreToRamEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Meas_m_Control_m_StoreToRam))
        self.NrMeasEdt.setText("{0:d}".format(l_DeviceData.m_StandAlone_m_Nmsr))                
        return

    @pyqtSlot()
    def on_WriteEepromBtn_clicked(self): 
        l_DeviceData = DeviceConfigType()
        l_DeviceData = AVS_GetParameter(globals.dev_handle, 63484)
        l_DeviceData.m_StandAlone_m_Meas_m_StartPixel = int(self.StartPixelEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_StopPixel =  int(self.StopPixelEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_IntegrationTime = float(self.IntTimeEdt.text())
        l_NanoSec = float(self.IntDelayEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0)
        l_DeviceData.m_StandAlone_m_Meas_m_NrAverages = int(self.AvgEdt.text())
        if (self.SoftwareTriggerRBtn.isChecked()):
            l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 0
        if (self.HardwareTriggerRBtn.isChecked()):
            l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 1
        if (self.SingleScanTriggerRBtn.isChecked()):
            l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 2
        l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source = self.SynchTriggerRBtn.isChecked()
        l_DeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType = self.LevelTriggerRBtn.isChecked()
        l_DeviceData.m_StandAlone_m_Meas_m_SaturationDetection = int(self.SatDetEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable = self.DarkCorrChk.isChecked()
        l_DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage = int(self.DarkCorrPercEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix = int(self.SmoothNrPixelsEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel = int(self.SmoothModelEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_Control_m_StrobeControl = int(self.FlashesPerScanEdt.text())
        l_NanoSec = float(self.LaserDelayEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserDelay = int(6.0*l_NanoSec/125.0)
        l_NanoSec = float(self.LaserWidthEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWidth = int(6.0*l_NanoSec/125.0)
        l_DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWaveLength = float(self.LaserWavEdt.text())
        l_DeviceData.m_StandAlone_m_Meas_m_Control_m_StoreToRam = int(self.NrStoreToRamEdt.text())
        l_DeviceData.m_StandAlone_m_Nmsr = int(self.NrMeasEdt.text())
        # write measurement parameters
        # debug = ctypes.sizeof(l_DeviceData)
        l_Ret = AVS_SetParameter(globals.dev_handle, l_DeviceData)
        if (0 != l_Ret):
            QMessageBox.critical(self, "Qt Demo", "AVS_SetParameter failed, code {0:d}".format(l_Ret))
        return        

    @pyqtSlot()
    def on_SpectrometerList_clicked(self):
        if (len(self.SpectrometerList.selectedItems()) != 0):
            self.UpdateButtons()
        return      

    def ConnectGui(self):
        versions = AVS_GetVersionInfo(globals.dev_handle)
        self.FPGAVerEdt.setText("{}".format(str(versions[0],"utf-8")))
        self.FirmwareVerEdt.setText("{}".format(str(versions[1],"utf-8")))
        self.DLLVerEdt.setText("{}".format(str(versions[2],"utf-8")))
        globals.DeviceData = DeviceConfigType()
        globals.DeviceData = AVS_GetParameter(globals.dev_handle, 63484)
        lDetectorName = AVS_GetDetectorName(globals.dev_handle, globals.DeviceData.m_Detector_m_SensorType)
        a_DetectorName = str(lDetectorName,"utf-8").split("\x00") 
        self.DetectorEdt.setText("{}".format(a_DetectorName[0]))
        if (globals.DeviceData.m_Detector_m_SensorType == SENS_HAMS9201):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(True)  # LowNoise default for HAMS9201
            self.HighSensitivityRBtn.setChecked(False)
            AVS_SetSensitivityMode(globals.dev_handle, 0)
        if (globals.DeviceData.m_Detector_m_SensorType == SENS_TCD1304):    
            self.PreScanChk.show()    
            self.PreScanChk.setCheckState(Qt.Checked)
            l_Res = AVS_SetPrescanMode(globals.dev_handle, self.PreScanChk.isChecked()) 
        if (globals.DeviceData.m_Detector_m_SensorType == SENS_SU256LSB):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(False)
            self.HighSensitivityRBtn.setChecked(True)  # High Sensitive default for SU256LSB
            l_Res = AVS_SetSensitivityMode(globals.dev_handle, 1)
        if (globals.DeviceData.m_Detector_m_SensorType == SENS_SU512LDB):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(False)
            self.HighSensitivityRBtn.setChecked(True)  # High Sensitive default for SU512LDB
            l_Res = AVS_SetSensitivityMode(globals.dev_handle, 1) 
        if (globals.DeviceData.m_Detector_m_SensorType == SENS_HAMG9208_512):
            self.SetNirSensitivityRgrp.show()
            self.LowNoiseRBtn.setChecked(True)  # low noise default
            self.HighSensitivityRBtn.setChecked(False)
            l_Res = AVS_SetSensitivityMode(globals.dev_handle, 0) 
        globals.pixels = globals.DeviceData.m_Detector_m_NrPixels
        self.NrPixelsEdt.setText("{0:d}".format(globals.pixels))
        globals.startpixel = globals.DeviceData.m_StandAlone_m_Meas_m_StartPixel
        globals.stoppixel = globals.DeviceData.m_StandAlone_m_Meas_m_StopPixel
        globals.wavelength = AVS_GetLambda(globals.dev_handle)
        return

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
        self.DstrStatusUpdateBtn.setEnabled(False)
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
        self.DstrStatusUpdateBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.StopMeasBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        self.ResetSpectrometerBtn.setEnabled(s == "USB_IN_USE_BY_APPLICATION" or s == "ETH_IN_USE_BY_APPLICATION")
        return 

    @pyqtSlot()
    def on_DeactivateBtn_clicked(self):
        ret = AVS_Deactivate(globals.dev_handle)
        globals.dev_handle = INVALID_AVS_HANDLE_VALUE
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
        l_Ret = AVS_ResetDevice( globals.dev_handle)
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
