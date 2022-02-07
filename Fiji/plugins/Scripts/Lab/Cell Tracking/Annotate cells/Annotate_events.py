"""
Use the point ROI tool to add points to the RoiManager inside of each cell you want to remove
then launch the script
"""

from ij import IJ
from ij.plugin.frame import RoiManager
from ij.gui import GenericDialog

from java.awt import Color as c

import Tracking.Results as Results
import Tracking.Cells as Cells

Replace = True

def SplitCellsAndPoints(RoiList):
    CellRois = []
    PointRois = []
    for Roi in RoiList:
        RoiName = Roi.getName()
        if RoiName[:4] == 'Cell':
            CellRois.append(Roi)
        else:
            PointRois.append(Roi)
    return CellRois, PointRois

def FindMatchingCell(PointRoi, CellRois):
    Frame = PointRoi.getZPosition()
    Xpoint = PointRoi.getContainedPoints()[0].x
    Ypoint = PointRoi.getContainedPoints()[0].y
    for CellRoi in CellRois:
        if CellRoi.getZPosition() == Frame:
            if CellRoi.contains(Xpoint, Ypoint):
                return CellRoi.getName().split('_')[0], Frame

def dialog():
    gd = GenericDialog('Annotate event')
    gd.addStringField('Event:', 'S-G2')
    gd.addStringField('Column:', 'Phase')
    gd.showDialog()
    Event = gd.getNextString()
    Column = gd.getNextString()
    return Event, Column

def run():
    Event, Column = dialog()

    imp = IJ.getImage()
    RM = RoiManager.getInstance()
    if not RM:
        RM = RoiManager()

    # Find where is ResultsRoot for current image
    ImgRoot = Results.get_rootpath(IJ.getDir('Image'))
    ResultsRoot = Results.results_root(ImgRoot)

    # Find names of currently selected cells
    RoiList = RM.getRoisAsArray()
    CellRois, PointRois = SplitCellsAndPoints(RoiList)
    CellNames = []
    for PointRoi in PointRois:
        CellNames.append(FindMatchingCell(PointRoi, CellRois))

    ### Load cells from ResultsRoot
    RM.reset()
    myCells = Cells.load_cells(ResultsRoot, RM)

    for myCell in myCells:
        i = 0
        while i < len(CellNames):
            if myCell.name == CellNames[i][0]:
                Slice = CellNames[i][1]
                myCell.annotate(Event, Slice, Column, replace=Replace)
                IJ.log(CellNames[i][0] + ' ' + str(CellNames[i][1]))
            i += 1

    Cells.save_cells(myCells, rm=None, ResultsRoot=ResultsRoot, SaveData=True, Prefix='0')
    IJ.log('Done.')

run()
