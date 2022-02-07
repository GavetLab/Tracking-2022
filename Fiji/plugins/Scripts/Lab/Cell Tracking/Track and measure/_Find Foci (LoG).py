# @Integer(label="Rolling Ball radius", value=2) RBradius
# @Integer(label="White Top Hat radius", value=4) WTHSmooth
# @Integer(label="LoG radius", value=4) LoGSmooth
# @Integer(label="FindMaxima tolerance", value=30) MaximaTolerance
# @String(label="Channel:", value='w2GFP') myChannel
# @String(label="Base name:", value='Foci') BaseName

# For PCNA: 0 0 2 140 works well!

from ij import IJ, ImagePlus
from ij.plugin.frame import RoiManager
from ij.plugin.filter import MaximumFinder
from ij.plugin import FolderOpener
from ij.gui import PointRoi
from inra.ijpb.morphology.strel import DiskStrel as Disk
from inra.ijpb.morphology import Morphology
from operator import itemgetter
import math
import os
import glob

# Import stuff from Erik Meijering (FeatureJ)
from imagescience.image import Image
from imagescience.feature import Laplacian

from java.awt import Color as c

# Import my own custom modules
from Tracking import Results, Cells

## Process pixels
def doLaplacian(ip):
    # White Top Hat
    if WTHSmooth > 0:
        myDisk = Disk.fromRadius(WTHSmooth)
        ip = Morphology.whiteTopHat(ip, myDisk)
    # Convert ip into an ImageScience 'Image'
    imp = ImagePlus('myImg', ip)
    img = Image.wrap(imp)
    # Perform Laplacian
    myLaplacian = Laplacian()
    L_img = myLaplacian.run(img, LoGSmooth)
    # Convert Image back into ip
    L_imp = L_img.imageplus()
    L_ip = L_imp.getProcessor()
    # Find maxima of ip
    L_ip.invert()
    MF = MaximumFinder()
    myPolygon = MF.getMaxima(L_ip, MaximaTolerance, True)
    MaximaList = []
    for (x,y) in zip(myPolygon.xpoints, myPolygon.ypoints):
        if x != 0 or y != 0:
            MaximaList.append((x,y))
    #print "foci", len(MaximaList)
    return MaximaList

def add_points_to_RM(MaximaList,RM,Slice):
    PointList = []
    for Maxima in MaximaList:
        pRoi = PointRoi(Maxima[0],Maxima[1])
        pRoi.setPosition(Slice)
        pRoi.setPointType(3)
        pRoi.setStrokeColor(c.red)
        RM.addRoi(pRoi)
        PointList.append(pRoi)
    return PointList

########################
def process_imp(myPath, RM):
    imp = FolderOpener.open(myPath)
    ImgRoot = Results.get_rootpath(myPath)
    ResultsRoot = Results.results_root(ImgRoot)
    myCells = Cells.load_cells(ResultsRoot, RM)
    #IJ.run(imp, "Gaussian Blur...", "sigma=2 stack")
    #IJ.run(imp, "Median...", "sigma=2 stack")
	
    if RBradius > 0:
        IJ.run(imp, 'Subtract Background...', 'rolling=' + str(RBradius) + ' stack')
    ip = imp.getProcessor()

    # List maxima in all frame
    maxFrame = imp.getNSlices()
    i = 1
    MaximaPerFrame = [[] for k in range(maxFrame)]
    while i <= maxFrame:
    	print i
        imp.setPosition(i)
        MaximaPerFrame[i - 1] = doLaplacian(ip)
        #PointList = add_points_to_RM(MaximaPerFrame[i-1],RM,i)
        i += 1
    
    # Test if maxima are in cells
    FociInCells = []
    for Cell in myCells:
        if not Cell.isExcluded():
            FociInCell = Cell.count_foci(MaximaPerFrame, BaseName, 'Nucleus')
            FociInCells.extend(FociInCell)
    Cells.save_cells(myCells, ResultsRoot=ResultsRoot, SaveData=True, Prefix='0')

    # Save FociROIs
    RM.reset()
    for FociRoi in FociInCells:
        RM.addRoi(FociRoi)
    RM.runCommand('Deselect')
    RM.runCommand('Save',os.path.join(ResultsRoot,'Foci_'+BaseName+'.zip'))

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

    RM.reset()
    IJ.log("Measuring...")
    for Pos in PosNames:
        IJ.log("  Position " + Pos)
        myPath = os.path.join(DataFolder, Pos, myChannel)
        process_imp(myPath, RM)
        RM.reset()
    IJ.log("Done.")

run()
