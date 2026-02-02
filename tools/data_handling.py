# -*- coding: utf-8 -*-
import os
import ctypes
import csv
import numpy as np
import pandas as pd
from datetime import datetime
from PyQt5.QtCore import (QDateTime)
import globals

class Logger:
    def __init__(self, filename, filetype):
        try:
            if filetype == "log":
                self.filename = self._get_unique_filename(filename)
                with open(self.filename, "x", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Cycle", "Time (YYYY-MM-DD_HH:MI:SS)", "Timestamp (s)", "Event"])
            elif filetype == "spectra":
                self.filename = self._get_unique_filename(filename)
                with open(self.filename, "x", newline="") as f:
                    writer = csv.writer(f)
            elif filetype == "load":
                self.filename = filename ## load file with known filename
        except:
            print("opening file was unsuccessful (unknown error)")

    def _get_unique_filename(self, base_filename):
        """
        If 'log.csv' exists, make 'log_2.csv', 'log_3.csv', etc.
        """
        if not os.path.exists(base_filename):
            return base_filename

        name, ext = os.path.splitext(base_filename)
        i = 2
        while os.path.exists(f"{name}_{i}{ext}"):
            i += 1
        return f"{name}_{i}{ext}"

    def log(self, event):
        time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
        timestamp = (globals.m_DateTime_start.msecsTo(QDateTime.currentDateTime()))/1000
        print(f"   timestamp: {timestamp}")
        
        with open(self.filename, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([globals.m_Cycle, time, timestamp, event])

    def save_wavelengths(self, wavelengths):
        df = pd.DataFrame({'Wavelengths (nm)': wavelengths})
        df.to_csv(self.filename, index=False)
        
    def build_df_spectra(self, spectrum, spectrum_number):
        '''
        Read .csv file as pandas dataframe.
        Add most recent spectrum as new column.
        Save new datafram as .csv under same name.
        '''
        df = pd.read_csv(self.filename)
        df[f"Spectrum {spectrum_number}"] = spectrum
        df.to_csv(self.filename, index=False)
    
    def load_df_spectra(self):
        '''
        Read .csv file as pandas dataframe.
        '''
        dataframe = pd.read_csv(self.filename)
        return dataframe
    
    def loaded_df_to_list(self, dataframe):
        values_column_1 = list(dataframe[dataframe.columns[1]])
        return values_column_1
    
    def save_spectrum(self, wavelengths, spectrum, data_header):
        ''' Save spectrum as .csv '''
        data_vstack = np.vstack((wavelengths, spectrum))
        data_transposed = np.transpose(data_vstack)
        xydata = pd.DataFrame(data_transposed,columns=["Wavelength (nm)", f"{data_header}"])
        xydata.to_csv(self.filename,index=False)
    
    def trace_wavelength(self, wavelength_of_interest):
        df = pd.read_csv(self.filename)
        closest_index = (df[df.columns[0]] - wavelength_of_interest).abs().idxmin()
        closest_wavelength = df.loc[closest_index, df.columns[0]]
        return closest_index, closest_wavelength

def append_filepath(filepath, appendage):
    name, ext = os.path.splitext(filepath)
    new_filepath = f"{name}_{appendage}{ext}"
    return new_filepath
        
def ConvertTimestamps(filename_log, filename_log_autoQY):
    ''' 
    Save corrected timestamps in a log file meant for autoQY:
    - generate time intervals from time logged between turning LED on and off,
      i.e. the actual irradiation time.
    - Re-create timestamps by doing a cumulative sum of the obtained intervals,
      after the addition of timestamps 0.0 s to the start of the array
    '''
    
    log = pd.read_csv(filename_log, sep = ",", decimal = ".")
    log_measure=log[log[log.columns[3]] == 'Measurement'] ## Measure lines in log file
    log_LEDon=log[log[log.columns[3]] == 'LED_ON']
    log_LEDoff=log[log[log.columns[3]] == 'LED_OFF']
    
    measure = log_measure.iloc[:, [2]].to_numpy() ## array of Measure instances
    timestamps_LEDon = log_LEDon.iloc[:, [2]].to_numpy()
    timestamps_LEDoff = log_LEDoff.iloc[:, [2]].to_numpy()
    timestamps_LEDon = timestamps_LEDon[:len(timestamps_LEDoff)]
    intervals_OffMinusOn = timestamps_LEDoff - timestamps_LEDon
    
    timestamps = np.cumsum(np.insert(intervals_OffMinusOn, 0, 0.0)) ## cumulative sum; add 0 to start
    
    if len(measure) != len(timestamps): ## remove final element in case of extra set of LEDon-LEDoff lines in log file
        timestamps = timestamps[:len(measure)]
        print(f"Cut timestamps array to length of Measure array: {len(measure)}")
    else:
        pass
    # print(f"timestamps len: {len(timestamps)}")

    indices = np.arange(len(timestamps))
    data_to_save = np.column_stack((indices, timestamps))

    np.savetxt(filename_log_autoQY, data_to_save, delimiter=",",
               header="index,timestamps of irradiation (s)",comments="",
               fmt=("%d","%.6f"))
    print(f"Saved log file for autoQY (with actual irradiation times) as: {filename_log_autoQY}")

    return

def doublearray_from_list(spectrum_list):
    """ Generate double-array from list """
    ArrayType = ctypes.c_double * 4096 ## ctypes array
    spectrum_doublearray = ArrayType(*spectrum_list) ## convert list to ctypes array
    return spectrum_doublearray

