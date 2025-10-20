# -*- coding: utf-8 -*-
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
import globals

# Matplotlib canvas class to create figure
class MplCanvas(Canvas):
    def __init__(self):
        self.fig = Figure(constrained_layout=True)
        self.ax = self.fig.add_subplot(111)
        Canvas.__init__(self, self.fig)
        Canvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        Canvas.updateGeometry(self)

class Plot(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)   # Inherit from QWidget
        self.canvas = MplCanvas()                  # Create canvas object
        self.vbl = QtWidgets.QVBoxLayout()         # Set box for plotting
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)

    def update_plot(self, spectrum):
        self.canvas.ax.clear()
        self.canvas.ax.set_xlabel("Wavelength (nm)")
        if globals.MeasurementType == "Dark":
            self.canvas.ax.set_ylabel("Counts")
        else:
            self.canvas.ax.set_ylabel("Counts (Dark- and SLS-Corrected)")
        # self.canvas.ax.plot(globals.wavelength, globals.ScopeSpectrum_DarkSLSCorr)
        self.canvas.ax.plot(globals.wavelength, spectrum)
        ############
        # self.canvas.ax.set_ylim(-100,3000)
        ############
        self.canvas.draw()
        self.show()    
        return

    def update_absorbanceplot(self):
        self.canvas.ax.clear()
        self.canvas.ax.set_xlabel("Wavelength (nm)")
        self.canvas.ax.set_ylabel("Absorbance")
        self.canvas.ax.plot(globals.wavelength, globals.AbsSpectrum)
        ############
        self.canvas.ax.set_xlim(250,1330)
        self.canvas.ax.set_ylim(-0.05,1.5)
        ############
        self.canvas.draw()
        self.show()
        return

    def recent_spectra(self, df):
        self.canvas.ax.clear()
        self.canvas.ax.set_xlabel("Wavelength (nm)")
        if globals.MeasurementMode == "Abs":
            self.canvas.ax.set_ylabel("Absorbance")
            self.canvas.ax.set_xlim(250,1330)
            self.canvas.ax.set_ylim(-0.05,1.5)
        elif globals.MeasurementMode == "Int":
            self.canvas.ax.set_ylabel("Counts (Dark- and SLS-Corrected)")
        ############
        for i in range(1,len(df.columns)):
            self.canvas.ax.plot(df[df.columns[0]],df[df.columns[i]])
        ############
        self.canvas.draw()
        self.show()
        print("plot recent spectra")
        return
    
    def trace(self, measurement_number, df, index_1, wavelength_1):
        self.canvas.ax.clear()
        self.canvas.ax.set_xlabel("Measurement")

        if globals.MeasurementMode == "Abs":
            self.canvas.ax.set_ylabel("Absorbance")
        elif globals.MeasurementMode == "Int":
            self.canvas.ax.set_ylabel("Counts (Dark- and SLS-Corrected)")

        range_of_measurements = np.arange(1,measurement_number+1)
        values_at_index_1 = df.iloc[index_1, 1:].to_numpy() ## Abs or Int values of each spectrum
        
        self.canvas.ax.scatter(range_of_measurements, values_at_index_1, 
                               color='darkorange', label=f'{wavelength_1:.1f} nm')
        self.canvas.ax.legend()
        self.canvas.draw()
        self.show()
        print("plot trace")


        