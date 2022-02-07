# Import FiJi modules
from ij import IJ, ImagePlus
from ij.plugin.frame import RoiManager
from ij.plugin import FolderOpener
from ij.gui import GenericDialog

# Import general use python modules
import os
import glob
import time

# Import my module to preprocess images
import Tracking.Segment as Segment

# Import my modules to manipulate 'Cell' objects and to save data
import Tracking.Cells as Cells
import Tracking.Results as Results

# Import my tracking algorithms
import Tracking.NucleiTracking as NucleiTracking

## GLOBAL SETTINGS ##
def dialog(DataFolder, ChannelNames, minPos, maxPos):
    myThresholding = {'Key': 'Simple Thresholding'}
    Methods = {
            'Nucleus 40x':'Gaussian_5 RBnoslide_38 Minimum_700 Mexican_5 Manual_2061 FillHoles Watershed PA_200-1000000_0.0-1',
            }

    # Dialog to ask for parameters
    ## Segmentation settings ##
    gd = GenericDialog("Parameters")
    gd.addMessage('Channel to use for segmentation:')
    gd.addChoice('Channel', ChannelNames, ChannelNames[0])

    gd.addMessage('Thresholding method:')
    gd.addChoice('Preset:', Methods.keys(), Methods.keys()[0])

    ## Tracking settings ##
    gd.addMessage('Tracking settings:')
    Inputs = [
            "External gradient"
            ]
    gd.addSlider('Max Distance:', 50, 150, 100)
    gd.addSlider('Watershed Sigma:', 2, 10, 5)
    gd.addChoice('Watershed input:', Inputs, Inputs[0])
    gd.addCheckbox('Backup matching using distance', True)

    ## Position settings ##
    gd.addMessage('Positions to process:')
    gd.addSlider('From:', minPos, maxPos, minPos)
    gd.addSlider('To:', minPos, maxPos, maxPos)

    gd.showDialog()

    if gd.wasCanceled():
        return None

    # Else, set values
    myChannel = gd.getNextChoice()
    myThresholding['Name'] = gd.getNextChoice()
    myThresholding['Method'] = Methods[myThresholding['Name']]
    maxDistance = gd.getNextNumber()
    w_sigma = int(gd.getNextNumber())
    w_input = gd.getNextChoice()
    BackupDistance = gd.getNextBoolean()
    firstPos = gd.getNextNumber()
    lastPos = gd.getNextNumber()
    myTracking = {'Max Distance':maxDistance, 'Watershed sigma':w_sigma, 'Watershed input':w_input, 'BackupDistance':BackupDistance}
    return myChannel, myThresholding, myTracking, firstPos, lastPos

###############################################

# What to do on each position
def process_position(RM, impPath, SegParam, TrackParam, PosValue):
    # Open image and find where to save Data
    imp = FolderOpener.open(impPath)
    ImgRoot = Results.get_rootpath(impPath)
    ResultsRoot = Results.results_root(ImgRoot)

    # Threshold
    IJ.log(" > Fetching ROIs from each frame...")
    RoiPerFrames = Segment.segment(imp, SegParam, RM)

    # Perform the actual tracking
    IJ.log(" > Matching Roi frame to frame...")
    myCells = NucleiTracking.track(RoiPerFrames, TrackParam, imp, PosValue)

    ## Save rois and write table
    IJ.log(" > Saving cells...")
    Cells.save_cells(myCells, ResultsRoot=ResultsRoot, rm=RM, SaveRois=True, SaveData=True, Prefix='0', Type='Nuclei')

def run():
    DataFolder = IJ.getDir('')
    RM = RoiManager.getInstance()
    if not RM:
        RM = RoiManager()
    os.chdir(DataFolder)

    # Test depth of folder to know where to search for positions folders
    testDepth = glob.glob('*/w*/')
    if testDepth:
        PosList = glob.glob("*/")
    else:
        PosList = glob.glob("*/*/")

    PosNames = []
    for Pos in PosList:
        os.chdir(os.path.join(DataFolder, Pos))
        ChannelPaths = glob.glob('w*/')
        if ChannelPaths:
            PosNames.append(Pos[:-1]) # Positions are assumed to be integers
    PosValues = [int(os.path.basename(os.path.normpath(Pos))) for Pos in PosNames]
    minPos = min(PosValues)
    maxPos = max(PosValues)
    ChannelNames = [Channel[:-1] for Channel in ChannelPaths]

    # Dialog box to ask for a few parameters
    myChannel, myThresholding, myTracking, firstPos, lastPos = dialog(DataFolder, ChannelNames, minPos, maxPos)

    # Process each position
    start = time.time()
    for Pos in PosNames:
        PosValue = int(os.path.basename(os.path.normpath(Pos)))
        if firstPos <= PosValue <= lastPos:
            IJ.log("\nPosition " + str(Pos))
            impPath = os.path.join(DataFolder, Pos, myChannel)
            process_position(RM, impPath, myThresholding, myTracking, PosValue)
    RM.reset()
    end = time.time()
    IJ.log("Done in " + str((end - start)/60) + ' min.')

run()
