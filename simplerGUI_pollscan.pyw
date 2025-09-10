#!/usr/bin/env python3
import os
import platform
import sys
import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from avaspec import *
import globals
from UIs import form1

class Worker(QObject):
    finished = pyqtSignal()
    func = None
    def run(self):
        self.func()
        self.finished.emit()
        return

class MainWindow(QMainWindow, form1.Ui_MainWindow):
    timer = QTimer()
    newdata = pyqtSignal(int, int)
    cancel = pyqtSignal()
    cancelled = False
    

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
        self.cancel.connect(self.cancel_meas)

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

    @pyqtSlot()
    def on_StartMeasBtn_clicked(self):
        ######################################################################
        ## Added QThread functionality
        
        try:
            if self.thread_qy.isRunning():
                print("Shutting down running thread.")
                self.thread_qy.terminate()
                time.sleep(1)
            else:
                print("No thread was running.")
        except:
            print("Didn't find thread.")
        self.thread_meas = QThread() # this creates an additional computing thread for processes, so the main window doesn't freeze
        self.worker_meas = Worker() # this is a worker that will tell when the job is done
        self.worker_meas.func = self.Kinetic_Measurement #here the job of the worker is defined. it should only be one function
        self.worker_meas.moveToThread(self.thread_meas) #the workers job is moved from the frontend to the thread in backend
        self.thread_meas.started.connect(self.worker_meas.run) # when the thread is started, the worker runs
        self.worker_meas.finished.connect(self.thread_meas.quit) # when the worker is finished, the thread is quit
        self.worker_meas.finished.connect(self.worker_meas.deleteLater)
        self.thread_meas.finished.connect(self.thread_meas.deleteLater)
        self.thread_meas.start() #here the thread is actually started
        
        print("Finished thread setup.")
        
        ######################################################################
        return

    @pyqtSlot()
    def Kinetic_Measurement(self):
        print("=== Kinetic_Measurement ===")
        self.StartMeasBtn.setEnabled(False)
        globals.NrScanned = 0
        nummeas = int(self.NumMeasEdt.text())
        delay = 2
        self.cancelled = False
        
        for i in range(nummeas):
            if self.cancelled == True: ## break loop if Stop button was pressed
                print("Stopped Kinetic Measurement")
                self.Shutter_Close()
                return
            else:
                print(f"for-loop===n\nnummeas: {nummeas}")
                self.One_Measurement()
                if globals.NrScanned != nummeas:
                    print(f"Waiting for {delay} s")
                    time.sleep(delay)
                    print(f"Delay {delay} s done")
        print(f"{nummeas} measurements done")
        self.StartMeasBtn.setEnabled(True)

    @pyqtSlot()
    def One_Measurement(self):
        print("=== One_Measurement ===")
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
        nummeas=1
        timestamp = 0
        print(f"globals.NrScanned: {globals.NrScanned}")

        ret = AVS_Measure(globals.dev_handle, 0, 1)
        globals.dataready = False
        print(f"globals.dataready: {globals.dataready}")
        self.Shutter_Open()
        while (globals.dataready == False):
            globals.dataready = (AVS_PollScan(globals.dev_handle) == True)
            time.sleep(0.001)
        if globals.dataready == True:
            timestamp, globals.spectraldata = AVS_GetScopeData(globals.dev_handle)
            globals.spectraldata = globals.spectraldata[:globals.pixels]
            self.newdata.emit(globals.dev_handle, ret)
            time.sleep(0.3)
        self.Shutter_Close()
        print("One Measurement done")
        return

    @pyqtSlot()
    def on_StopMeasBtn_clicked(self):
        # ret = AVS_StopMeasure(globals.dev_handle)
        print("=== StopMeasBtn clicked ===")
        self.cancel.emit()
        time.sleep(1)
        self.StartMeasBtn.setEnabled(True)
        return

    @pyqtSlot()
    def cancel_meas(self):
        ret = AVS_StopMeasure(globals.dev_handle)
        self.cancelled = True
        return

    @pyqtSlot()
    def update_plot(self):
        self.plot.update_plot()
        if (globals.NrScanned == int(self.NumMeasEdt.text())):
            self.StartMeasBtn.setEnabled(True)    
        return        

    @pyqtSlot(int,int)
    def handle_newdata(self, ldev_handle, lerror):
        ''' for PollScan method '''
        if (lerror >= 0):
            ##!!! the input for ldev_handle is globals.dev_handle, so seems redundant
            if ((ldev_handle == globals.dev_handle) and (globals.pixels > 0)):
                # self.statusBar.showMessage("Meas.Status: success")
                print("=== handle_newdata ===")
                try:
                    print(f"globals.dataready: {globals.dataready}")
                    globals.NrScanned += 1  
                    self.update_plot()
                except:
                    print("new data was not handled")
        return

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget{font-size:10px}")
    app.lastWindowClosed.connect(app.quit)
    app.setApplicationName("PyQt5 simple demo")
    form = MainWindow()
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
