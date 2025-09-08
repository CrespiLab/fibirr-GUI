# -*- coding: utf-8 -*-
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from UIs import eeprom
from avaspec import *
import globals

class EepromDialog(QDialog, eeprom.Ui_Eeprom):
    DeviceData = DeviceConfigType()
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.ShowForm()

    def convert(self, stringvalue, boolvalue):
        if boolvalue[0] == False:
           return 0.0
        else:     
            try:
                boolvalue[0] = True
                floatvalue = float(stringvalue)
                return floatvalue
            except ValueError:
                boolvalue[0] = False
                return 0.0

    def convert_to_ip(self, stringvalue, boolvalue):
        if boolvalue[0] == False:
           return 0
        else:
            try:   
                iptext = stringvalue.split('.')
                part1 = int(iptext[0])
                part2 = int(iptext[1])
                part3 = int(iptext[2])
                part4 = int(iptext[3])
                value = part1 | (part2<<8) | (part3<<16) | (part4<<24)
                return value
            except ValueError:
                boolvalue[0] = False
                return 0    

    @pyqtSlot()
    def on_SaveEepromBtn_clicked(self):
        self.DeviceData = AVS_GetParameter(globals.dev_handle, 63484)
        test = [True]
        self.DeviceData.m_ConfigVersion = int(self.convert(self.StrucVersionEdt.text(), test))
        self.DeviceData.m_aUserFriendlyId = str.encode(self.FriendlyEdt.text())
        if (self.SensorComboBox.currentIndex() >= 0): # value is -1 when not set
            self.DeviceData.m_Detector_m_SensorType = self.SensorComboBox.currentIndex() + SENSOR_OFFSET
        self.DeviceData.m_Detector_m_NrPixels = int(self.convert(self.NrPixelsEdt.text(), test))
        self.DeviceData.m_Detector_m_aFit[0] = float(self.convert(self.WavCalInterceptEdt.text(), test))
        self.DeviceData.m_Detector_m_aFit[1] = float(self.convert(self.WavCalX1Edt.text(), test))
        self.DeviceData.m_Detector_m_aFit[2] = float(self.convert(self.WavCalX2Edt.text(), test))
        self.DeviceData.m_Detector_m_aFit[3] = float(self.convert(self.WavCalX3Edt.text(), test))
        self.DeviceData.m_Detector_m_aFit[4] = float(self.convert(self.WavCalX4Edt.text(), test))
        self.DeviceData.m_Detector_m_Gain[0] = float(self.convert(self.Gain1Edt.text(), test))
        self.DeviceData.m_Detector_m_Gain[1] = float(self.convert(self.Gain2Edt.text(), test))
        self.DeviceData.m_Detector_m_Offset[0] = float(self.convert(self.Offset1Edt.text(), test))
        self.DeviceData.m_Detector_m_Offset[1] = float(self.convert(self.Offset2Edt.text(), test))
        self.DeviceData.m_Detector_m_ExtOffset = float(self.convert(self.ExtOffsetEdt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[0] = float(self.convert(self.NonLinInterceptEdt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[1] = float(self.convert(self.NonLinX1Edt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[2] = float(self.convert(self.NonLinX2Edt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[3] = float(self.convert(self.NonLinX3Edt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[4] = float(self.convert(self.NonLinX4Edt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[5] = float(self.convert(self.NonLinX5Edt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[6] = float(self.convert(self.NonLinX6Edt.text(), test))
        self.DeviceData.m_Detector_m_aNLCorrect[7] = float(self.convert(self.NonLinX7Edt.text(), test))
        self.DeviceData.m_Detector_m_aLowNLCounts = float(self.convert(self.LoCountsEdt.text(), test))
        self.DeviceData.m_Detector_m_aHighNLCounts = float(self.convert(self.HiCountsEdt.text(), test))
        self.DeviceData.m_Detector_m_NLEnable = self.NonLinEnableChk.isChecked()
        defecttext = self.DefectEdt.toPlainText().split('\n')
        i = 0
        while (i < NR_DEFECTIVE_PIXELS) and (i < len(defecttext)):
            self.DeviceData.m_Detector_m_DefectivePixels[i] = int(self.convert(defecttext[i], test)) 
            i += 1
        # Get standalone parameters
        self.DeviceData.m_StandAlone_m_Enable = self.EnableStandAloneChk.isChecked()
        self.DeviceData.m_StandAlone_m_Meas_m_StartPixel = int(self.convert(self.StartPixelEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_StopPixel =  int(self.convert(self.StopPixelEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_IntegrationTime = float(self.convert(self.IntTimeEdt.text(), test))
        l_NanoSec = float(self.convert(self.IntDelayEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_IntegrationDelay = int(6.0*(l_NanoSec+20.84)/125.0)
        self.DeviceData.m_StandAlone_m_Meas_m_NrAverages = int(self.convert(self.NrAveragesEdt.text(), test))
        if (self.SoftwareTriggerRBtn.isChecked()):
            self.DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 0
        if (self.HardwareTriggerRBtn.isChecked()):
            self.DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 1
        if (self.SingleScanTriggerRBtn.isChecked()):
            self.DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode = 2
        self.DeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source = self.SynchTriggerRBtn.isChecked()
        self.DeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType = self.LevelTriggerRBtn.isChecked()
        self.DeviceData.m_StandAlone_m_Meas_m_SaturationDetection = int(self.SatDetectEdt.text())
        self.DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable = self.DarkCorrEnableChk.isChecked()
        self.DeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage = int(self.convert(self.DarkPercentageEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix = int(self.convert(self.SmoothPixelsEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel = int(self.convert(self.SmoothModelEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_Control_m_StrobeControl = int(self.convert(self.FlashesPerScanEdt.text(), test))
        l_NanoSec = float(self.convert(self.LaserDelayEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserDelay = int(6.0*l_NanoSec/125.0)
        l_NanoSec = float(self.convert(self.LaserWidtEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWidth = int(6.0*l_NanoSec/125.0)
        self.DeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWaveLength = float(self.convert(self.LaserWavEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Meas_m_Control_m_StoreToRam = int(self.convert(self.StoreToRamEdt.text(), test))
        self.DeviceData.m_StandAlone_m_Nmsr = int(self.convert(self.NrMeasEdt.text(), test))
        # Get Irradiance parameters
        self.DeviceData.m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothModel = int(self.convert(self.IrradianceSmoothModelEdt.text(), test))
        self.DeviceData.m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothPix = int(self.convert(self.IrradianceSmoothPixelsEdt.text(), test))
        self.DeviceData.m_Irradiance_m_IntensityCalib_m_CalInttime = float(self.convert(self.IrradianceIntTimeEdt.text(), test))
        irradiancetext = self.IrradianceConvEdt.toPlainText().split('\n')
        i = 0
        while (i < MAX_NR_PIXELS) and (i < len(irradiancetext)):
            self.DeviceData.m_Irradiance_m_IntensityCalib_m_aCalibConvers[i] = float(self.convert(irradiancetext[i], test)) 
            i += 1
        self.DeviceData.m_Irradiance_m_CalibrationType = int(self.convert(self.IrradCalibrationTypeEdt.text(), test))
        self.DeviceData.m_Irradiance_m_FiberDiameter = int(self.convert(self.IrradFiberDiameterEdt.text(), test))
        # Get Reflectance parameters
        self.DeviceData.m_Reflectance_m_Smoothing_m_SmoothModel = int(self.convert(self.ReflectanceSmoothModelEdt.text(), test))
        self.DeviceData.m_Reflectance_m_Smoothing_m_SmoothPix = int(self.convert(self.ReflectanceSmoothPixelsEdt.text(), test))
        self.DeviceData.m_Reflectance_m_CalInttime = float(self.convert(self.ReflectanceIntTimeEdt.text(), test))
        reflectancetext = self.ReflectanceCorrEdt.toPlainText().split('\n')
        i = 0
        while (i < MAX_NR_PIXELS) and (i < len(reflectancetext)):
            self.DeviceData.m_Reflectance_m_aCalibConvers[i] = float(self.convert(reflectancetext[i], test)) 
            i += 1
        # Get Correction parameters
        correctiontext = self.SpectrumCorrEdt.toPlainText().split('\n')
        i = 0
        while (i < MAX_NR_PIXELS) and (i < len(correctiontext)):
            self.DeviceData.m_SpectrumCorrect[i] = float(self.convert(correctiontext[i], test)) 
            i += 1
        # Get Thermistor parameters
        self.DeviceData.m_Temperature_1_m_aFit[0] = float(self.convert(self.NTC1X0Edt.text(), test))
        self.DeviceData.m_Temperature_1_m_aFit[1] = float(self.convert(self.NTC1X1Edt.text(), test))
        self.DeviceData.m_Temperature_1_m_aFit[2] = float(self.convert(self.NTC1X2Edt.text(), test))
        self.DeviceData.m_Temperature_1_m_aFit[3] = float(self.convert(self.NTC1X3Edt.text(), test))
        self.DeviceData.m_Temperature_1_m_aFit[4] = float(self.convert(self.NTC1X4Edt.text(), test))
        self.DeviceData.m_Temperature_2_m_aFit[0] = float(self.convert(self.NTC2X0Edt.text(), test))
        self.DeviceData.m_Temperature_2_m_aFit[1] = float(self.convert(self.NTC2X1Edt.text(), test))
        self.DeviceData.m_Temperature_2_m_aFit[2] = float(self.convert(self.NTC2X2Edt.text(), test))
        self.DeviceData.m_Temperature_2_m_aFit[3] = float(self.convert(self.NTC2X3Edt.text(), test))
        self.DeviceData.m_Temperature_2_m_aFit[4] = float(self.convert(self.NTC2X4Edt.text(), test))
        self.DeviceData.m_Temperature_3_m_aFit[0] = float(self.convert(self.ThermistorX0Edt.text(), test))
        self.DeviceData.m_Temperature_3_m_aFit[1] = float(self.convert(self.ThermistorX1Edt.text(), test))
        self.DeviceData.m_Temperature_3_m_aFit[2] = float(self.convert(self.ThermistorX2Edt.text(), test))
        self.DeviceData.m_Temperature_3_m_aFit[3] = float(self.convert(self.ThermistorX3Edt.text(), test))
        self.DeviceData.m_Temperature_3_m_aFit[4] = float(self.convert(self.ThermistorX4Edt.text(), test))
        # Get Tec Control parameters
        self.DeviceData.m_TecControl_m_Enable = self.TECEnableChk.isChecked()
        self.DeviceData.m_TecControl_m_Setpoint = float(self.convert(self.SetPointEdt.text(), test))
        self.DeviceData.m_TecControl_m_aFit[0] = float(self.convert(self.TECX0Edt.text(), test))
        self.DeviceData.m_TecControl_m_aFit[1] = float(self.convert(self.TECX1Edt.text(), test))
        # Get Ethernet/DHCP settings
        self.DeviceData.m_EthernetSettings_m_IpAddr = self.convert_to_ip(self.IpAddressEdt.text(), test)
        self.DeviceData.m_EthernetSettings_m_NetMask = self.convert_to_ip(self.NetMaskEdt.text(), test)
        self.DeviceData.m_EthernetSettings_m_Gateway = self.convert_to_ip(self.GatewayEdt.text(), test)
        self.DeviceData.m_EthernetSettings_m_TcpPort = int(self.convert(self.TcpPortEdt.text(), test))
        self.DeviceData.m_EthernetSettings_m_DhcpEnabled = self.DhcpEnabledChk.isChecked()
        self.DeviceData.m_EthernetSettings_m_LinkStatus = self.LinkStatusChk.isChecked()
        if (self.ClientIdNoneRBtn.isChecked()):
            self.DeviceData.m_EthernetSettings_m_ClientIdType = 0
        if (self.ClientIdMacRBtn.isChecked()):
            self.DeviceData.m_EthernetSettings_m_ClientIdType = 1
        if (self.ClientIdSerialRBtn.isChecked()):
           self.DeviceData.m_EthernetSettings_m_ClientIdType = 2
        if (self.ClientIdCustomRBtn.isChecked()):
            self.DeviceData.m_EthernetSettings_m_ClientIdType = 3
            if len(self.CustomClientIdEdt.text()) < CLIENT_ID_SIZE:
                self.DeviceData.m_EthernetSettings_m_ClientIdCustom = str.encode(self.CustomClientIdEdt.text())
            else:
                test[0] = False
        # Write parameters
        if (test[0] == True):
            # l_Ret = AVS_SetParameter(globals.dev_handle, self.DeviceData)
            l_Ret = 0
            if (0 != l_Ret):
                QMessageBox.critical(self, "Qt Demo", "AVS_SetParameter failed, code {0:d}".format(l_Ret))
        else:
           QMessageBox.critical(self, "Qt Demo", "Invalid Data Input!")             
        return

    @pyqtSlot()
    def on_UseFactorySettingsBtn_clicked(self):
        l_Ret = AVS_ResetParameter(globals.dev_handle)
        if (0 != l_Ret):
            QMessageBox.critical(self, "Qt Demo", "AVS_ResetParameter failed, code {0:d}".format(l_Ret))
            return
        else:
            self.DeviceData = AVS_GetParameter(globals.dev_handle, 63484)
            self.ShowDataInForm(self.DeviceData)
            QMessageBox.information(self, "Qt Demo", "Spectrometer factory settings restored!")
        return

    def ShowForm(self):
        # test FW version
        testversion = (1<<24) | (9<<16) | (6<<8) | 0   # 1.9.6.0
        versions = AVS_GetVersionInfo(globals.dev_handle)
        FWversionstring = str(versions[1],"utf-8").rstrip('\x00')
        FWversiontext = FWversionstring.split('.')
        part1 = int(FWversiontext[0])
        part2 = int(FWversiontext[1])
        part3 = int(FWversiontext[2])
        part4 = int(FWversiontext[3])
        FWversionnum = (part1<<24) | (part2<<16) | (part3<<8) | part4 
        self.DeviceData = AVS_GetParameter(globals.dev_handle, 63484)
        self.ShowDataInForm(self.DeviceData)
        if (FWversionnum >= testversion):
           self.dhcpOptionEnabledLabel.hide() 
        else:
           self.dhcpOptionEnabledLabel.show()
           self.dhcpOptionEnabledLabel.setStyleSheet("QLabel { color : red; }")
           self.dhcpOptionEnabledLabel.setText("Current spectrometer firmware version {} does not support the DHCP Client ID option!".format(FWversionstring))
        return
    
    def ShowDataInForm(self, apDeviceData):
        self.tabWidget.setCurrentWidget(self.DetectorTab)
        self.StrucLengthEdt.setText("{0:d}".format(apDeviceData.m_Len))
        self.StrucVersionEdt.setText("{0:d}".format(apDeviceData.m_ConfigVersion))
        self.FriendlyEdt.setText("{}".format(str(apDeviceData.m_aUserFriendlyId,"utf-8"))) 
        # show detectortype parameters
        self.SensorComboBox.clear()
        lsensor = 1
        while lsensor < NUMBER_OF_SENSOR_TYPES:
           lname = AVS_GetDetectorName(globals.dev_handle, lsensor)
           namestring =  str(lname,"utf-8").split("\x00") 
           self.SensorComboBox.addItem(namestring[0])
           lsensor += 1
        if (apDeviceData.m_Detector_m_SensorType < NUMBER_OF_SENSOR_TYPES):
           self.SensorComboBox.setCurrentIndex(apDeviceData.m_Detector_m_SensorType - SENSOR_OFFSET)
        self.NrPixelsEdt.setText("{0:d}".format(apDeviceData.m_Detector_m_NrPixels))
        self.WavCalInterceptEdt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aFit[0]))
        self.WavCalX1Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aFit[1]))
        self.WavCalX2Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aFit[2]))
        self.WavCalX3Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aFit[3]))
        self.WavCalX4Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aFit[4]))
        self.Gain1Edt.setText("{0:.2f}".format(apDeviceData.m_Detector_m_Gain[0]))
        self.Gain2Edt.setText("{0:.2f}".format(apDeviceData.m_Detector_m_Gain[1]))
        self.Offset1Edt.setText("{0:.2f}".format(apDeviceData.m_Detector_m_Offset[0]))
        self.Offset2Edt.setText("{0:.2f}".format(apDeviceData.m_Detector_m_Offset[1]))
        self.ExtOffsetEdt.setText("{0:.2f}".format(apDeviceData.m_Detector_m_ExtOffset))
        self.NonLinInterceptEdt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[0]))
        self.NonLinX1Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[1]))
        self.NonLinX2Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[2]))
        self.NonLinX3Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[3]))
        self.NonLinX4Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[4]))
        self.NonLinX5Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[5]))
        self.NonLinX6Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[6]))
        self.NonLinX7Edt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aNLCorrect[7]))
        self.LoCountsEdt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aLowNLCounts))
        self.HiCountsEdt.setText("{0:.8e}".format(apDeviceData.m_Detector_m_aHighNLCounts))    
        self.NonLinEnableChk.setChecked(apDeviceData.m_Detector_m_NLEnable)
        self.DefectEdt.clear()
        i = 0
        while i < NR_DEFECTIVE_PIXELS:
            self.DefectEdt.append("{0:d}".format(apDeviceData.m_Detector_m_DefectivePixels[i]))
            i += 1
        # show standalone parameters
        self.EnableStandAloneChk.setChecked(apDeviceData.m_StandAlone_m_Enable)
        self.StartPixelEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_StartPixel))
        self.StopPixelEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_StopPixel))
        self.IntTimeEdt.setText("{0:.3f}".format(apDeviceData.m_StandAlone_m_Meas_m_IntegrationTime))
        l_FPGAClkCycles = apDeviceData.m_StandAlone_m_Meas_m_IntegrationDelay
        l_NanoSec = 125.0*(l_FPGAClkCycles - 1.0) / 6.0;
        self.IntDelayEdt.setText("{0:.0f}".format(l_NanoSec))
        self.NrAveragesEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_NrAverages))
        self.SatDetectEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_SaturationDetection))
        self.SoftwareTriggerRBtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 0)
        self.HardwareTriggerRBtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 1)
        self.SingleScanTriggerRBtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_Mode == 2)
        self.ExternalTriggerRbtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source == 0)
        self.SynchTriggerRBtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_Source == 1)
        self.EdgeTriggerRBtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType == 0)
        self.LevelTriggerRBtn.setChecked(apDeviceData.m_StandAlone_m_Meas_m_Trigger_m_SourceType == 1)
        self.DarkCorrEnableChk.setChecked(apDeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_Enable == 1)
        self.DarkPercentageEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_CorDynDark_m_ForgetPercentage))
        self.SmoothModelEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothModel))
        self.SmoothPixelsEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_Smoothing_m_SmoothPix))
        self.FlashesPerScanEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_Control_m_StrobeControl))
        l_FPGAClkCycles = apDeviceData.m_StandAlone_m_Meas_m_Control_m_LaserDelay
        l_NanoSec = 125.0*(l_FPGAClkCycles) / 6.0
        self.LaserDelayEdt.setText("{0:.0f}".format(l_NanoSec))
        l_FPGAClkCycles = apDeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWidth
        l_NanoSec = 125.0*(l_FPGAClkCycles) / 6.0
        self.LaserWidtEdt.setText("{0:.0f}".format(l_NanoSec))
        self.LaserWavEdt.setText("{0:.3f}".format(apDeviceData.m_StandAlone_m_Meas_m_Control_m_LaserWaveLength))
        self.StoreToRamEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Meas_m_Control_m_StoreToRam))
        self.NrMeasEdt.setText("{0:d}".format(apDeviceData.m_StandAlone_m_Nmsr))
        # show irradiance parameters
        self.IrradianceSmoothModelEdt.setText("{0:d}".format(apDeviceData.m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothModel))
        self.IrradianceSmoothPixelsEdt.setText("{0:d}".format(apDeviceData.m_Irradiance_m_IntensityCalib_m_Smoothing_m_SmoothPix))
        self.IrradianceIntTimeEdt.setText("{0:.3f}".format(apDeviceData.m_Irradiance_m_IntensityCalib_m_CalInttime))
        self.IrradianceConvEdt.clear()
        i = 0
        while i < MAX_NR_PIXELS:
            self.IrradianceConvEdt.append("{0:.8e}".format(apDeviceData.m_Irradiance_m_IntensityCalib_m_aCalibConvers[i]))
            i += 1
        self.IrradCalibrationTypeEdt.setText("{0:d}".format(apDeviceData.m_Irradiance_m_CalibrationType))
        self.IrradFiberDiameterEdt.setText("{0:d}".format(apDeviceData.m_Irradiance_m_FiberDiameter))
        # show reflectance parameters
        self.ReflectanceSmoothModelEdt.setText("{0:d}".format(apDeviceData.m_Reflectance_m_Smoothing_m_SmoothModel))
        self.ReflectanceSmoothPixelsEdt.setText("{0:d}".format(apDeviceData.m_Reflectance_m_Smoothing_m_SmoothPix))
        self.ReflectanceIntTimeEdt.setText("{0:.3f}".format(apDeviceData.m_Reflectance_m_CalInttime))
        self.ReflectanceCorrEdt.clear()
        i = 0
        while i < MAX_NR_PIXELS:
            self.ReflectanceCorrEdt.append("{0:.8e}".format(apDeviceData.m_Reflectance_m_aCalibConvers[i]))
            i += 1
        # show correction parameters
        self.SpectrumCorrEdt.clear()
        i = 0
        while i < MAX_NR_PIXELS:
            self.SpectrumCorrEdt.append("{0:.8e}".format(apDeviceData.m_SpectrumCorrect[i]))
            i += 1
        # show thermistor parameters
        self.NTC1X0Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_1_m_aFit[0]))
        self.NTC1X1Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_1_m_aFit[1]))
        self.NTC1X2Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_1_m_aFit[2]))
        self.NTC1X3Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_1_m_aFit[3]))
        self.NTC1X4Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_1_m_aFit[4]))
        self.NTC2X0Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_2_m_aFit[0]))
        self.NTC2X1Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_2_m_aFit[1]))
        self.NTC2X2Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_2_m_aFit[2]))
        self.NTC2X3Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_2_m_aFit[3]))
        self.NTC2X4Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_2_m_aFit[4]))
        self.ThermistorX0Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_3_m_aFit[0]))
        self.ThermistorX1Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_3_m_aFit[1]))
        self.ThermistorX2Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_3_m_aFit[2]))
        self.ThermistorX3Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_3_m_aFit[3]))
        self.ThermistorX4Edt.setText("{0:.8e}".format(apDeviceData.m_Temperature_3_m_aFit[4]))
        # show TEC Control parameters
        self.TECEnableChk.setChecked(apDeviceData.m_TecControl_m_Enable)
        self.SetPointEdt.setText("{0:.1f}".format(apDeviceData.m_TecControl_m_Setpoint))
        self.TECX0Edt.setText("{0:.3f}".format(apDeviceData.m_TecControl_m_aFit[0]))
        self.TECX1Edt.setText("{0:.3f}".format(apDeviceData.m_TecControl_m_aFit[1]))       
        # show Ethernet settings
        self.IpAddressEdt.setText("{0:d}.{1:d}.{2:d}.{3:d}".format(apDeviceData.m_EthernetSettings_m_IpAddr & 0xff,
                                                                  (apDeviceData.m_EthernetSettings_m_IpAddr >> 8) & 0xff,
                                                                  (apDeviceData.m_EthernetSettings_m_IpAddr >> 16) & 0xff,
                                                                  (apDeviceData.m_EthernetSettings_m_IpAddr >> 24)))
        self.NetMaskEdt.setText("{0:d}.{1:d}.{2:d}.{3:d}".format(apDeviceData.m_EthernetSettings_m_NetMask & 0xff,
                                                                (apDeviceData.m_EthernetSettings_m_NetMask >> 8) & 0xff,
                                                                (apDeviceData.m_EthernetSettings_m_NetMask >> 16) & 0xff,
                                                                (apDeviceData.m_EthernetSettings_m_NetMask >> 24)))
        self.GatewayEdt.setText("{0:d}.{1:d}.{2:d}.{3:d}".format(apDeviceData.m_EthernetSettings_m_Gateway & 0xff,
                                                                (apDeviceData.m_EthernetSettings_m_Gateway >> 8) & 0xff,
                                                                (apDeviceData.m_EthernetSettings_m_Gateway >> 16) & 0xff,
                                                                (apDeviceData.m_EthernetSettings_m_Gateway >> 24)))                                                                  
        self.TcpPortEdt.setText("{0:d}".format(apDeviceData.m_EthernetSettings_m_TcpPort))
        self.DhcpEnabledChk.setChecked(apDeviceData.m_EthernetSettings_m_DhcpEnabled == 1)
        self.LinkStatusChk.setChecked(apDeviceData.m_EthernetSettings_m_LinkStatus == 1)
        self.ClientIdNoneRBtn.setChecked(apDeviceData.m_EthernetSettings_m_ClientIdType == 0)
        self.ClientIdMacRBtn.setChecked(apDeviceData.m_EthernetSettings_m_ClientIdType == 1)
        self.ClientIdSerialRBtn.setChecked(apDeviceData.m_EthernetSettings_m_ClientIdType == 2)
        self.ClientIdCustomRBtn.setChecked(apDeviceData.m_EthernetSettings_m_ClientIdType == 3)
        self.CustomClientIdEdt.setText("{}".format(str(apDeviceData.m_EthernetSettings_m_ClientIdCustom,"utf-8")))

        return
