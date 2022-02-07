from ij import IJ
from ij.gui import GenericDialog
from ij.plugin import FolderOpener
from ij.plugin.frame import RoiManager

import Tracking.Results as Results
import Tracking.Cells as Cells

import os
import glob

#################################################

class Measurement:
    def __init__(self, Type):
        self.Type = Type # Either "Shape" or Channel name (w1GFP...)
        self.Compartments = {} # Dictionary of lists {'Nucleus': ['Mean', 'Median'], 'Cytoplasm': ['Kurtosis']}

class MeasurePosition:
    def __init__(self, Pos, MeasureList, RollingBall):
        os.chdir(Pos)
        self.Pos = Pos
        self.MeasureList = MeasureList
        self.RollingBall = RollingBall
        self.ResultsRoot = Results.results_root(Pos)

    def analyze(self, RM):
        self.Cells = Cells.load_cells(self.ResultsRoot, RM)
        for myMeasurement in self.MeasureList:
            Type = myMeasurement.Type
            IJ.log("   " + Type)
            if Type != "Shape":
                path = os.path.join(self.Pos, myMeasurement.Type)
                imp = FolderOpener.open(path)
                if self.RollingBall:
                    IJ.run(imp, "Subtract Background...", "rolling=" + str(self.RollingBall) + " stack")
            elif Type == "Shape":
                #TODO: it won't work if only measuring shape!
                imp = FolderOpener.open(path)
            for Compartment, Keys in myMeasurement.Compartments.items():
                for myCell in self.Cells:
                    myCell.measure_channel(imp, Type, Keys, Compartment)
            imp.close()
        Cells.save_cells(self.Cells, ResultsRoot=self.ResultsRoot, SaveData=True, Prefix='0')

#################################################

def Dialog(ChannelNames, CompartmentList):
    MeasureList = []
    for Channel in ChannelNames:
        MeasureList.append(Measurement(Channel))
    MeasureList.append(Measurement("Shape"))

    # Ask what channels user wants to process
    gd = GenericDialog("Parameters")
    gd.addMessage('Which channel(s) do you want to measure?')
    for myMeasurement in MeasureList:
        gd.addMessage(myMeasurement.Type)
        for Compartment in CompartmentList:
            gd.addCheckbox(Compartment, False)
    gd.addNumericField('Rolling Ball radius:', 38, 0)
    gd.showDialog()
    # Exit if canceled
    if gd.wasCanceled():
        exit()
    # Find which channels you want to measure
    for myMeasurement in MeasureList:
        gd.addMessage(myMeasurement.Type)
        for Compartment in CompartmentList:
            if gd.getNextBoolean():
                myMeasurement.Compartments[Compartment] = []
    RollingBall = gd.getNextNumber()

    # For each channel, determine which parameters you want to measure
    ShapeKeys = ['Area', 'Perimeter', 'Centroid', 'Circularity', 'Feret']
    ChannelKeys = ['Mean', 'Median', 'Min', 'Max', 'StD', 'Kurtosis', 'Skewness']
    trueMeasureList = []
    for myMeasurement in MeasureList:
        if myMeasurement.Compartments:
            trueMeasureList.append(myMeasurement)
            # Generate dialog
            gd = GenericDialog("Parameters")
            gd.addMessage(myMeasurement.Type)
            for Compartment in myMeasurement.Compartments.keys():
                gd.addMessage(Compartment)
                if Compartment == "Shape":
                    for ShapeKey in ShapeKeys:
                        gd.addCheckbox(ShapeKey, False)
                else:
                    for Key in ChannelKeys:
                        gd.addCheckbox(Key, False)
            gd.showDialog()
            # Exit if canceled
            if gd.wasCanceled():
                exit()
            # Get data from dialog
            for Compartment in myMeasurement.Compartments.keys():
                if Compartment == "Shape":
                    for Key in ShapeKeys:
                        if gd.getNextBoolean():
                            myMeasurement.Compartments[Compartment].append(Key)
                else:
                    for Key in ChannelKeys:
                        if gd.getNextBoolean():
                            myMeasurement.Compartments[Compartment].append(Key)
    return trueMeasureList, RollingBall

def run():
    DataFolder = IJ.getDir('')
    RM = RoiManager.getInstance()
    if not RM:
        RM = RoiManager()
    os.chdir(DataFolder)
    testDepth = glob.glob('*/w*/')
    if testDepth:
        PosList = glob.glob("*/")
    else:
        PosList = glob.glob("*/*/")

    # Keep only folders containing channels
    # and find list of channels
    PosNames = []
    ChannelNames = []
    for Pos in PosList:
        os.chdir(os.path.join(DataFolder, Pos))
        ChannelPaths = glob.glob('w*/')
        if ChannelPaths:
            PosNames.append(Pos)
            if not ChannelNames:
                ChannelNames = [Channel[:-1] for Channel in ChannelPaths]
    PosNames.sort()

    # Find ROI compartments (Nucleus, Cytoplasm, FullCell)
    # For this to work, the first Pos need to have ROIs!
    ResultsRoot = Results.results_root(os.path.join(DataFolder, PosNames[0]))
    os.chdir(ResultsRoot)
    NucleiRoi = glob.glob('*_Nuclei_ROI.zip')
    CytoRoi = glob.glob('*_Cytoplasms_ROI.zip')
    FullRoi = glob.glob('*_FullCells_ROI.zip')
    CompartmentList = []
    if NucleiRoi: CompartmentList.append('Nucleus')
    if CytoRoi: CompartmentList.append('Cytoplasm')
    if FullRoi: CompartmentList.append('Full Cell')

    # Dialog box to ask for a few parameters
    MeasureList, RollingBall = Dialog(ChannelNames, CompartmentList)

    RM.reset()
    IJ.log("Measuring...")
    for Pos in PosNames:
        IJ.log("  Position " + Pos)
        Measure = MeasurePosition(os.path.join(DataFolder, Pos), MeasureList, RollingBall)
        Measure.analyze(RM)
        RM.reset()
    IJ.log("Done.")

run()
