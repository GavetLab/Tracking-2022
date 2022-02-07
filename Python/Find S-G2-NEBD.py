#!/usr/bin/env python
import pandas as pd
import numpy as np

import glob
import os

##############
## Settings ##
##############

## Look for:
fG1S = False
fSG2 = True
fNEBD = True

# To find S/G2 transition:
SG2Channel = 'w3Ruby optional Nucleus Max' # set to none if you don't want to look for G2
# Which method to use to detect S/G2 transition ('Slope' or 'MaxVar')
SG2Method = 'Slope'
#SG2Method = 'MaxVar'

# G2: Slope method
SG2_angle = 0 # 'angle' must be below this threshold
# G2: Max variation method:
G2_max = -0.3 # at least 30% decrease in Max channel

# To find NEBD:
#NEBDChannel = 'w4Ruby optional Nucleus Mean'
NEBDChannel = 'w2CFPex YFPem FRET Nucleus Mean'
NEBD_mean = -0.3 # at least 30% decrease in Mean channel

# To find G1/S transition
G1SChannel = 'w3Ruby optional Nucleus Mean'
G1_angle = 0 # 'angle' must be below this threshold
SG2_angle = -40000 # 'angle' must be below this threshold

##############
##############

def SG2_transitionSLOPE(Table, Cell, CellIndex):
    if not SG2Channel: # Won't look for G2 if no MeanChannel
        return False
    # Median filter the plot
    myCell = Cell.loc[CellIndex]
    myCell['MedianMean'] = myCell[SG2Channel].rolling(7, center=True,min_periods=0).median()
    # Compute linear regression
    window = 15
    MeanValues = myCell['MedianMean'].values
    slope_before = [None]*len(myCell)
    for n in range(window, len(myCell)+1):
        y = MeanValues[(n-window):n]
        x = range(n-window,n)
        a,b = np.polyfit(x,y,1)
        slope_before[n-1] = a
    # Use .shift(window) method to have slope after timepoint
    myCell['slope b'] = slope_before
    myCell['slope a'] = myCell['slope b'].shift(1-window)
    myCell['angle'] = (myCell['slope a'] - myCell['slope b'])*myCell['slope b']
    # Find minimum angle and return it if found
    MinTable = myCell[(myCell['slope b'] < -150) & (myCell['angle'] < SG2_angle)]
    if not MinTable.empty:
        MinAng_idx = MinTable['angle'].idxmin()
        return MinAng_idx
    else:
        return False

def G1S_transition(Table, Cell, CellIndex):
    if not G1SChannel: # Won't look for G2 if no MeanChannel
        return False
    # Median filter the plot
    myCell = Cell.loc[CellIndex]
    myCell['MedianMean'] = pd.rolling_median(myCell[G1SChannel], window=5, center=True, min_periods=0)
    # Compute linear regression
    window = 10
    MeanValues = myCell['MedianMean'].values
    #slope_before = pd.Series([None]*len(myCell), index=CellIndex)
    slope_before = [None]*len(myCell)
    for n in range(window, len(myCell)+1):
        y = MeanValues[(n-window):n]
        x = range(n-window,n)
        a,b = np.polyfit(x,y,1)
        #slope_before.set_value(n-1, a)
        slope_before[n-1] = a
    # Use .shift(window) method to have slope after timepoint
    #slope_before = pd.to_numeric(slope_before, errors='coerce')
    #slope_after = slope_before.shift(1 - window)
    myCell['slope b'] = slope_before
    myCell['slope a'] = myCell['slope b'].shift(1-window)
    #Cell['angle'] = (Cell['slope b'] - Cell['slope a'])/(1- Cell['slope b']*Cell['slope a'])
    myCell['angle'] = myCell['slope b']*myCell['slope a']
    # Find minimum angle and return it if found
    #MinTable = Cell[(Cell['slope a'] > 0) & (Cell['angle'] < G1_angle)]
    MinTable = myCell[(myCell['slope a'] > 12) & (myCell['angle'] < G1_angle)]
    if not MinTable.empty:
        MinAng_idx = MinTable['angle'].idxmin()
        return MinAng_idx
    else:
        return False

def SG2_transitionMAXVAR(Table, Cell, CellIndex):
    if not SG2Channel: # Won't look for G2 if no MaxChannel
        return False
    Table.loc[CellIndex, 'MaxDiff'] = Cell[SG2Channel].diff()
    MaxVar_idx = Table.loc[CellIndex, 'MaxDiff'].idxmin()
    AfterPeak = Table.loc[CellIndex].loc[MaxVar_idx:]
    G2_idx = AfterPeak[AfterPeak['MaxDiff'] > 0].head(1).index
    BeforePeak = Table.loc[CellIndex].loc[:MaxVar_idx]
    LastS_idx = BeforePeak[BeforePeak['MaxDiff'] > 0].tail(1).index
    G2val = Table.loc[G2_idx, SG2Channel].values
    Sval = Table.loc[LastS_idx, SG2Channel].values
    Table.drop('MaxDiff', axis=1, inplace=True)

    # Compare the found S/G2 transition max value with the value in S phase
    if G2val < Sval*(1+G2_max):
        return G2_idx[0]
    else:
        return False

def NEBD(Table, Cell, myIndex):
    if not NEBDChannel: # Won't look for G2 if no MeanChannel
        return False
    Table.loc[myIndex, 'MeanDiff'] = Cell[NEBDChannel].diff()
    Table.loc[myIndex, 'MeanVar'] = Table.loc[myIndex, 'MeanDiff']/Table.loc[myIndex, NEBDChannel].shift(1)
    myTable = Table.loc[myIndex]
    MeanVars = myTable[myTable['MeanVar'] < NEBD_mean]
    Table.drop(['MeanVar', 'MeanDiff'], axis=1, inplace=True)
    if not MeanVars.empty:
        NEBDmean_idx = MeanVars['MeanVar'].idxmin()
        return NEBDmean_idx
    else:
        return False

################################

def process_pos(path):
    Table = pd.read_csv(path, sep='\t')
    SingleCells = Table.groupby('Name')
    if 'Phase' in Table.columns:
        Table = Table.drop('Phase', 1)

    for CellName, Cell in SingleCells:
        CellIndex = Cell.index
        # Look for cell phase transitions
        if fNEBD:
            NEBD_idx = NEBD(Table, Cell, CellIndex)
            if not NEBD_idx == False:
                CellIndex = Table.loc[CellIndex].loc[:NEBD_idx].index
                Table.loc[NEBD_idx, 'Phase'] = 'NEBD'
        if fSG2:
            if SG2Method == 'Slope':
                G2_idx = SG2_transitionSLOPE(Table, Cell, CellIndex)
            if SG2Method == 'Slope v2':
                G2_idx = SG2_transitionSLOPEv2(Table, Cell, CellIndex)
            if SG2Method == 'MaxVar':
                G2_idx = SG2_transitionMAXVAR(Table, Cell, CellIndex)
            if not G2_idx == False:
                CellIndex = Table.loc[CellIndex].loc[:G2_idx].index
                Table.loc[G2_idx, 'Phase'] = 'S-G2'

        if fG1S:
            G1_idx = G1S_transition(Table, Cell, CellIndex)
            if not G1_idx == False: # G1-S found
                Table.loc[G1_idx, 'Phase'] = 'G1-S'
    Table.to_csv(path, sep='\t', index=False)

###############################

testDepth = glob.glob('RAW/*/*/0_Table.tsv')
if testDepth:
    tsvlist = testDepth
else:
    tsvlist = glob.glob('RAW/*/0_Table.tsv')

for path in tsvlist:
    print(path)
    process_pos(path)
