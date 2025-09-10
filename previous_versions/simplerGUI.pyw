#!/usr/bin/env python3
import os
import platform
import sys
import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from avaspec import *
import globals
from UIs import form1

# import form1

class MainWindow(QMainWindow, form1.Ui_MainWindow):
    timer = QTimer()
    newdata = pyqtSignal(int, int)

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.IntTimeEdt.setText("{:3.1f}".format(5.0))
        self.NumAvgEdt.setText("{0:d}".format(1))
        self.NumMeasEdt.setText("{0:d}".format(1))
        self.StartMeasBtn.setEnabled(False)
#       self.OpenCommBtn.clicked.connect(self.on_OpenCommBtn_clicked)
#       For the buttons, do not use explicit connect together with the on_ notation, 
#       or you will get two signals instead of one!
        self.timer.timeout.connect(self.update_plot)
        # self.timer.start(200)
        self.newdata.connect(self.handle_newdata)

    def measure_cb(self, pparam1, pparam2):
        param1 = pparam1[0] # dereference the pointers
        param2 = pparam2[0]
        self.newdata.emit(param1, param2) 

    @pyqtSlot()
#   if you leave out the @pyqtSlot() line, you will also get an extra signal!
#   so you might even get three!
    def on_OpenCommBtn_clicked(self):
        ret = AVS_Init(0)    
        # QMessageBox.information(self,"Info","AVS_Init returned:  {0:d}".format(ret))
        ret = AVS_GetNrOfDevices()
        # QMessageBox.information(self,"Info","AVS_GetNrOfDevices returned:  {0:d}".format(ret))
        if (ret > 0):
            mylist = AvsIdentityType * 1
            mylist = AVS_GetList(1)
            serienummer = str(mylist[0].SerialNumber.decode("utf-8"))
            QMessageBox.information(self,"Info","Found Serialnumber: " + serienummer)
            globals.dev_handle = AVS_Activate(mylist[0])
            # QMessageBox.information(self,"Info","AVS_Activate returned:  {0:d}".format(globals.dev_handle))
            devcon = DeviceConfigType()
            devcon = AVS_GetParameter(globals.dev_handle, 63484)
            globals.pixels = devcon.m_Detector_m_NrPixels
            globals.wavelength = AVS_GetLambda(globals.dev_handle)
            self.StartMeasBtn.setEnabled(True)
        else:
            QMessageBox.critical(self,"Error","No devices were found!") 
        return

    @pyqtSlot()
    def on_CloseCommBtn_clicked(self):
        # nothing for now
        return

    def Shutter_Open(self):
        # ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_OPEN) ## open shutter
        print(">>>Shutter opened<<<")
        delay_s = 0.3
        time.sleep(delay_s) ## short delay between Open Shutter and Measure
        
    def Shutter_Close(self):
        # time.sleep(delay_b) ##!!! small delay necessary maybe, but ideally command should wait for acquisition to be finished
        # ava.AVS_SetDigOut(globals.dev_handle, portID_pin12_DO4, SHUTTER_CLOSE) ## close shutter
        print(">>>Shutter closed<<<")
        delay_s = 0.1
        time.sleep(delay_s) ## short delay between Measure and Close Shutter

    # @pyqtSlot()
    # def on_StartMeasBtn_clicked(self):
    #     print("StartMeasBtn clicked")
    #     self.StartMeasBtn.setEnabled(False)
    #     ret = AVS_UseHighResAdc(globals.dev_handle, True)
    #     measconfig = MeasConfigType()
    #     measconfig.m_StartPixel = 0
    #     measconfig.m_StopPixel = globals.pixels - 1
    #     measconfig.m_IntegrationTime = float(self.IntTimeEdt.text())
    #     measconfig.m_IntegrationDelay = 0
    #     measconfig.m_NrAverages = int(self.NumAvgEdt.text())
    #     measconfig.m_CorDynDark_m_Enable = 0  # nesting of types does NOT work!!
    #     measconfig.m_CorDynDark_m_ForgetPercentage = 0
    #     measconfig.m_Smoothing_m_SmoothPix = 0
    #     measconfig.m_Smoothing_m_SmoothModel = 0
    #     measconfig.m_SaturationDetection = 0
    #     measconfig.m_Trigger_m_Mode = 0
    #     measconfig.m_Trigger_m_Source = 0
    #     measconfig.m_Trigger_m_SourceType = 0
    #     measconfig.m_Control_m_StrobeControl = 0
    #     measconfig.m_Control_m_LaserDelay = 0
    #     measconfig.m_Control_m_LaserWidth = 0
    #     measconfig.m_Control_m_LaserWaveLength = 0.0
    #     measconfig.m_Control_m_StoreToRam = 0
    #     # self.timer.start(200)

    #     ret = AVS_PrepareMeasure(globals.dev_handle, measconfig)
    #     nummeas = int(self.NumMeasEdt.text())
    #     print(f"===StartMeas\n======nummeas: {nummeas}")
    #     globals.NrScanned = 0
    #     print(f"======globals.NrScanned: {globals.NrScanned}")
    #     # l_Res = AVS_MeasureCallback(globals.dev_handle, avs_cb, nummeas)
    #     # while nummeas != globals.NrScanned: # wait until data has arrived
    #     while globals.NrScanned < nummeas:
    #         avs_cb = AVS_MeasureCallbackFunc(self.measure_cb)
    #         l_Res = AVS_MeasureCallback(globals.dev_handle, avs_cb, 1)
    #         globals.dataready = False
    #         print(f"===StartMeas\n======globals.dataready: {globals.dataready}")
    #         self.Shutter_Open()
    #         while (globals.dataready == False):
    #             # print(f"===on_StartMeasBtn_clicked\n======l_Res: {l_Res}")
    #             # print(f"globals.NrScanned: {globals.NrScanned}")
    #             time.sleep(0.001)
    #             qApp.processEvents()
    #             # print(f"globals.dataready: {globals.dataready}")
    #         self.Shutter_Close()
    #         delay = 5
    #         if globals.NrScanned != nummeas:
    #             time.sleep(delay)
    #             print(f"Delay {delay} s done")
    #     self.StartMeasBtn.setEnabled(True)      
    #     print("Measurement done")
    #     return

    @pyqtSlot()
    def on_StartMeasBtn_clicked(self):
        nummeas = int(self.NumMeasEdt.text())
        delay = 5
        
        for i in range(nummeas):
            print(f"===StartMeasBtn\n======nummeas: {nummeas}")

        
            self.One_Measurement()
            
            if globals.NrScanned != nummeas:
                print(f"Waiting for {delay} s")
                time.sleep(delay)
                # print(f"Delay {delay} s done")
        
        self.StartMeasBtn.setEnabled(True)      
        return

    def One_Measurement(self):
        print("One_Measurement")
        self.StartMeasBtn.setEnabled(False)
        ret = AVS_UseHighResAdc(globals.dev_handle, True)
        measconfig = MeasConfigType()
        measconfig.m_StartPixel = 0
        measconfig.m_StopPixel = globals.pixels - 1
        measconfig.m_IntegrationTime = float(self.IntTimeEdt.text())
        measconfig.m_IntegrationDelay = 0
        measconfig.m_NrAverages = int(self.NumAvgEdt.text())
        measconfig.m_CorDynDark_m_Enable = 0  # nesting of types does NOT work!!
        measconfig.m_CorDynDark_m_ForgetPercentage = 0
        measconfig.m_Smoothing_m_SmoothPix = 0
        measconfig.m_Smoothing_m_SmoothModel = 0
        measconfig.m_SaturationDetection = 0
        measconfig.m_Trigger_m_Mode = 0
        measconfig.m_Trigger_m_Source = 0
        measconfig.m_Trigger_m_SourceType = 0
        measconfig.m_Control_m_StrobeControl = 0
        measconfig.m_Control_m_LaserDelay = 0
        measconfig.m_Control_m_LaserWidth = 0
        measconfig.m_Control_m_LaserWaveLength = 0.0
        measconfig.m_Control_m_StoreToRam = 0
        # self.timer.start(200)

        ret = AVS_PrepareMeasure(globals.dev_handle, measconfig)
        # nummeas = int(self.NumMeasEdt.text())
        nummeas=1
        # print(f"===OneMeas\n======nummeas: {nummeas}")
        globals.NrScanned = 0
        print(f"======globals.NrScanned: {globals.NrScanned}")
        # l_Res = AVS_MeasureCallback(globals.dev_handle, avs_cb, nummeas)
        # while nummeas != globals.NrScanned: # wait until data has arrived
        avs_cb = AVS_MeasureCallbackFunc(self.measure_cb)
        l_Res = AVS_MeasureCallback(globals.dev_handle, avs_cb, 1)
        globals.dataready = False
        print(f"===OneMeas\n======globals.dataready: {globals.dataready}")
        self.Shutter_Open()
        while (globals.dataready == False):
            # print(f"===on_StartMeasBtn_clicked\n======l_Res: {l_Res}")
            # print(f"globals.NrScanned: {globals.NrScanned}")
            time.sleep(0.001)
            qApp.processEvents()
            # print(f"globals.dataready: {globals.dataready}")
        self.Shutter_Close()

        # self.StartMeasBtn.setEnabled(True)      
        print("One Measurement done")
        return



    @pyqtSlot()
    def on_StopMeasBtn_clicked(self):
        ret = AVS_StopMeasure(globals.dev_handle)
        self.StartMeasBtn.setEnabled(True)
        return

    @pyqtSlot()
    def update_plot(self):
        self.plot.update_plot()
        if (globals.NrScanned == int(self.NumMeasEdt.text())):
            self.StartMeasBtn.setEnabled(True)    
        return        

    @pyqtSlot(int, int)
    def handle_newdata(self, lparam1, lparam2):
        globals.dataready = True
        print(f"===handle_newdata\n======globals.dataready: {globals.dataready}")
        #print(lparam1)
        #print(lparam2)
        timestamp = 0
        ret = AVS_GetScopeData(globals.dev_handle)
        timestamp = ret[0]
        globals.NrScanned += 1  
        print(f"======globals.NrScanned: {globals.NrScanned}")
        globals.spectraldata = ret[1]
        self.update_plot() ## update plot
        
        # QMessageBox.information(self,"Info","Received data")
        return

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget{font-size:10px}")
    app.lastWindowClosed.connect(app.quit)
    app.setApplicationName("PyQt5 simple demo")
    form = MainWindow()
    form.show()
    app.exec_()

main()
