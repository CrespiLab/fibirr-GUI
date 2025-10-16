# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

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

