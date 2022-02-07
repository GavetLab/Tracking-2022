from ij import IJ, WindowManager 
from ij.gui import Plot, GenericDialog, NonBlockingGenericDialog, YesNoCancelDialog
from ij.plugin.frame import RoiManager

from java.awt import Color as c

import Tracking.Cells as Cells
import Tracking.Results as Results

from operator import itemgetter

##############
## SETTINGS ##
##############

# Cells to include in the review:
ToInclude = {
        "G1-S":('G1-S','Phase'),
        "S-G2":('S-G2','Phase'),
        "NEBD":('NEBD','Phase'),
        "Included cells":('True','Included'),
        "All at t0":('1','Slice')
        }

# Dictionnaries of features to measure:
ToMeasureNum = {
        "1st CK":[0,0,False,'Phase','CK1',1],
        "G1-S":[0,0,False,'Phase','G1-S',2],
        "Mid S":[0,0,False,'Phase','MidS',3],
        "Late S":[0,0,False,'Phase','LateS',4],
        "S-G2":[0,0,True,'Phase','S-G2',5],
        "S-G2 (last foci)":[0,0,False,'Phase','Last Foci',6],
        "NEBD":[0,0,True,'Phase','NEBD',7],
        "Anaphase":[0,0,False,'Phase','Anaphase',8],
        "FRET earlyS inc":[0,0,False,'FRETvar','FRET-Sinc',9],
        "FRET lateS max":[0,0,False,'FRETvar','FRET-lSmax',10],
        "FRET earlyG2 min":[0,0,False,'FRETvar','FRET-lSmin',11],
        "FRET G2 inc":[0,0,True,'FRETvar','FRET-G2incr',12],
        "FRET G2 max":[0,0,False,'FRETvar','FRET-G2max',13],
        "FRET G2 decr":[0,0,True,'FRETvar','FRET-G2decr',14],
        "FRET G2 min":[0,0,False,'FRETvar','FRET-G2min',15],
        "FRET late inc":[0,0,True,'FRETvar','FRET-lateInc',16]
        }

ToMeasureBool = {
        "G2>Mitosis":[False,False,False,'G2 fate','Mit',1],
        "G2>Delay>Mitosis":[False,False,False,'G2 fate','Delay-Mit',2],
        "G2>Arrest":[False,False,False,'G2 fate','Arrest',3],
        "Lagging Chrom.":[False,False,False,'Bool','Lagging',4],
        "Lost Track":[False,False,True,'Bool','Lost Track',5],
        "Lost":[False,False,True,'Bool','Lost',6],
        "Pretty cell":[False,False,True,'Bool','Pretty',7],
        }

# Windows coordinates 
ScreenConfigs = {
        'Macbook Pro (Retina 13)': {
                "wDial_x": 832,
                "wDial_y": 56,
                "wPlot_x": 769,
                "wPlot_y": 423,
                },

        'Macbook pro (1280x800)': {
                "wDial_x": 740,
                "wDial_y": 50,
                "wPlot_x": 675,
                "wPlot_y": 376,
                },

        'Macbook air (1440x900)': {
                "wDial_x": 740,
                "wDial_y": 50,
                "wPlot_x": 675,
                "wPlot_y": 376,
                },

        'iMac (1920x1080)': {
                "wDial_x": 1050,
                "wDial_y": 150,
                "wPlot_x": 1050,
                "wPlot_y": 600,
                },
            }

#################################################################

toAndOr = [
	"Or",
        "And"
        ]

def sort_dict(Dict):
    List = []
    for Key in Dict.keys():
        Order = Dict[Key][5]
        List.append([Key, Order])
    List.sort(key=itemgetter(1))
    List = [item[0] for item in List]
    return List

def window_coord(Title, x, y):
    myWindow = WindowManager.getWindow(Title)
    myWindow.setLocation(x, y)

def get_window_coord(Title):
    myWindow = WindowManager.getWindow(Title)

def plot_data(WindowName, Xlabel, Ylabel, x, y):
    myPlot = Plot(WindowName, Xlabel, Ylabel, x, y)
    myPlot.setColor(c.red)
    myPlot.setLineWidth(2)
    return myPlot

def getSerie(label, myCell):
    mySerie = [float(Slice[label]) for Slice in myCell.Table]
    return mySerie

def dialog(myCell):
    gd = GenericDialog('Annotate event')
    TimeFields = []
    allowedTime = ['Slice']
    for Field in myCell.Fields:
        if Field in allowedTime:
            TimeFields.append(Field)
    gd.addChoice('X:', TimeFields, 'Slice')
    if "1/FRET" in myCell.Fields:
        defaultY = '1/FRET'
    else:
        defaultY = myCell.Fields[-1]
    gd.addChoice('Y:', myCell.Fields, defaultY)

    ## Add choices for ROI colors
    AllowedColors = ['One color per cell']
    DefaultColor = 'One color per cell'
    if "Included" in myCell.Fields:
        AllowedColors.append('Included are green')
        DefaultColor = 'Included are green'
    if "Phase" in myCell.Fields:
        AllowedColors.append('Color with cell cycle')
        DefaultColor = 'Color with cell cycle'

    colorlist = {
            'One color per cell':'',
            'Included are green':'Included',
            'Color with cell cycle':'Phase v2',
            }

    gd.addChoice('Nuclei color:', AllowedColors, DefaultColor)
    gd.addChoice('Screen config:', ScreenConfigs.keys(), ScreenConfigs.keys()[0])
    gd.showDialog()
    xlabel = gd.getNextChoice()
    ylabel = gd.getNextChoice()
    colorchoice = gd.getNextChoice()
    Screen = gd.getNextChoice()
    ScreenConfig = ScreenConfigs[Screen]

    color = colorlist[colorchoice]

    return xlabel, ylabel, color, ScreenConfig

def dialogSelectIncluded():
    gd = GenericDialog('Select cells to include:')
    for item in ToInclude.keys():
        gd.addCheckbox(item, False)
    gd.addChoice('And/Or?:',toAndOr,toAndOr[0])
    gd.showDialog()
    IncDict = {}
    for item in ToInclude.keys():
        if gd.getNextBoolean():
            IncDict.update({item:ToInclude[item]})
    howInc = gd.getNextChoice()
    return IncDict,howInc

def dialogSelectMeasure():
    gd = GenericDialog('Select events to review')
    gd.addMessage("Event timing:")
    NumList = sort_dict(ToMeasureNum)
    BoolList = sort_dict(ToMeasureBool)
    for item in NumList:
        gd.addCheckbox(item, ToMeasureNum[item][2])
    gd.addMessage("Event (y/n):")
    for item in BoolList:
        gd.addCheckbox(item, ToMeasureBool[item][2])
    gd.showDialog()
    NumDict = {}
    for item in NumList:
        if gd.getNextBoolean():
            NumDict.update({item:list(ToMeasureNum[item])})
    BoolDict = {}
    for item in BoolList:
        if gd.getNextBoolean():
            BoolDict.update({item:list(ToMeasureBool[item])})
    return NumDict, BoolDict

def dialog_with_phase(minX,maxX,NumDict, BoolDict, isIncluded,ScreenConfig):
    # Create dialog asking value for each feature to measure
    gd = NonBlockingGenericDialog('Slice of event')
    NumList = sort_dict(NumDict)
    for Feature in NumList:
        gd.addSlider(Feature, minX, maxX, NumDict[Feature][0], minX)
    BoolList = sort_dict(BoolDict)
    for Feature in BoolList:
        gd.addCheckbox(Feature, BoolDict[Feature][0])
    gd.addCheckbox('Included?', True)
    gd.addCheckbox('Excluded?', False)
    gd.enableYesNoCancel('Next', 'Exit')
    gd.setCancelLabel('Prev')

    # Display dialog
    gd.setLocation(ScreenConfig['wDial_x'],ScreenConfig['wDial_y'])
    gd.showDialog()
    if gd.wasCanceled():
        return 0, 0, 0, 0, 1
    if gd.wasOKed():
        # Get the data back
        for Feature in NumList:
            NumDict[Feature][1] = gd.getNextNumber()
        for Feature in BoolList:
            BoolDict[Feature][1] = gd.getNextBoolean()
        Included = gd.getNextBoolean()
        Excluded = gd.getNextBoolean()
        return NumDict,BoolDict, Included, Excluded, 2
    else:
        return 0, 0, 0, 0, 0

def drawLine(Slice, Color, myPlot):
    xMin, xMax, yMin, yMax = myPlot.getLimits()
    myPlot.setColor(c.black)
    myPlot.add('line', [Slice, Slice], [0, 10000])

def go_to_cell(imp, myCell, SG2):
    # Go to the frame with SG2 transition
    # And change color of Roi to cyan
    imp.setPosition(SG2)
    Roi = myCell.getRoiAt(SG2)
    imp.setRoi(Roi)
    Roi.setColor(c.cyan)

def doIincludeCell(myCell, IncDict,howInc):
    QuantifyCell = False
    for Feat in IncDict.keys():
        Values = myCell.get_occurences(IncDict[Feat][0], IncDict[Feat][1])
        if Values:
            QuantifyCell = True
        elif howInc == "And":
            return False
    return QuantifyCell

def makeListOfCells(AllCells, IncDict, howInc):
    SelectedCells = []
    for myCell in AllCells:
        QuantifyCell = doIincludeCell(myCell, IncDict,howInc)
        if QuantifyCell:
            SelectedCells.append(myCell)
    return SelectedCells

def plot_each_cell(myCell, xlabel, ylabel, imp, IncDict,howInc,NumDict,BoolDict,ScreenConfig, CellNum, Total):
    # Get data from cell
    Xdata = getSerie(xlabel, myCell)
    Ydata = getSerie(ylabel, myCell)

    isIncluded = myCell.get_occurences('True', 'Included')
    if isIncluded: isIncluded = True
    else: isIncluded = False
    ExitStatus = None
    
    # Get values if already exist
    for Feat in NumDict.keys():
        Values = myCell.get_occurences(NumDict[Feat][4], NumDict[Feat][3])
        if Values:
            NumDict[Feat][0] = int(Values[0])
        else:
            NumDict[Feat][0] = ToMeasureNum[Feat][0]
    for Feat in BoolDict.keys():
        Values = myCell.get_occurences(BoolDict[Feat][4], BoolDict[Feat][3])
        if Values: BoolDict[Feat][0] = True
        else: BoolDict[Feat][0] = ToMeasureBool[Feat][0]
    
    WindowName = myCell.name +' ('+str(CellNum)+'/'+str(Total)+')'
    myPlot = plot_data(WindowName, xlabel, ylabel, Xdata, Ydata)

    # Annotate plot and mark cell in movie
    SG2time = 0
    NEBDtime = 0
    if "S-G2" in NumDict.keys():
        SG2time = NumDict['S-G2'][0]
        if SG2time != 0:
            drawLine(SG2time, c.red, myPlot)
    if "NEBD" in NumDict.keys():
        NEBDtime = NumDict['NEBD'][0]
        if NEBDtime != 0:
            drawLine(NEBDtime, c.green, myPlot)
    if SG2time:
        go_to_cell(imp, myCell, SG2time)
    elif NEBDtime:
        go_to_cell(imp, myCell, NEBDtime)
    else:
        go_to_cell(imp, myCell, int(Xdata[0]))


    # Display plot and move it to appropiate coordinates
    myPlot.show()
    window_coord(WindowName, ScreenConfig['wPlot_x'],ScreenConfig['wPlot_y'])

    # Make the image the active window instead of the plot
    imgWindow = imp.getWindow()
    imgWindow.toFront()

    # Dialog to ask for the value
    NumDict,BoolDict, Included, Excluded, ExitStatus = dialog_with_phase(0,Xdata[-1],NumDict, BoolDict, isIncluded, ScreenConfig)

    if ExitStatus == 1:
        imp = myPlot.getImagePlus()
        imp.close()
        return 'CANCEL'
    if ExitStatus == 0:
        imp = myPlot.getImagePlus()
        imp.close()
        return 'EXIT'

    if Excluded == True:
        myCell.exclude_cell('True')
    else:
        # Compare previous value to new value and edit cell if value changed
        for Feat in NumDict.keys():
            prevVal = NumDict[Feat][0]
            newVal = NumDict[Feat][1]
            if prevVal != newVal:
                EventName = NumDict[Feat][4]
                ColumnName = NumDict[Feat][3]
                # If newVal == 0, it will be removed from table
                myCell.annotate(EventName, newVal, ColumnName, replace=True)
                ExitStatus = 'EDIT'
        i = 0
        for Feat in BoolDict.keys():
            prevVal = BoolDict[Feat][0]
            newVal = BoolDict[Feat][1]
            if prevVal != newVal:
                EventName = BoolDict[Feat][4]
                ColumnName = BoolDict[Feat][3]
                if max(Xdata) - 1 < 1:
                    IJ.log('Not enough rows in cell ' + str(myCell.name) + ' to annotate ' + str(EventName))
                else:
                    ExitStatus = 'EDIT'
                    if newVal == True:
                        myCell.annotate(EventName, max(Xdata) - i, ColumnName, replace=True)
                    else:
                        # If newVal == False, it will be removed from table
                        myCell.annotate(EventName, 0, ColumnName, replace=True)
                i += 1
        if Included != isIncluded:
            myCell.include_cell(Included)
    imp = myPlot.getImagePlus()
    imp.close()
    return ExitStatus

def run():
    RM = RoiManager.getInstance()
    if not RM:
        RM = RoiManager()
    imp = IJ.getImage()

    RM.reset()

    RM.runCommand("Associate", "true")
    RM.runCommand("Centered", "false")
    RM.runCommand("UseNames", "true")

    # Find path to results root (where table is saved)
    ImpRoot = Results.get_rootpath(IJ.getDir('Image'))
    ResultsRoot = Results.results_root(ImpRoot)

    # Load data about cell of interest
    RM.runCommand(imp,"Show None")    
    myCells = Cells.load_cells(ResultsRoot, RM)

    # Ask what to plot
    xlabel, ylabel, NucleiColor, ScreenConfig = dialog(myCells[0])
    IncDict, howInc = dialogSelectIncluded()
    NumDict, BoolDict = dialogSelectMeasure()

    # Load cells to ROI manager
    Cells.save_cells(myCells, rm=RM, Type='Nuclei', color=NucleiColor)
    RM.runCommand(imp,"Show All")

    # Display plot for each cell
    CellList = makeListOfCells(myCells, IncDict, howInc)
    i = 0
    j = 0
    CellNumber = len(CellList)
    while i < CellNumber:
        myCell = CellList[i]
        ExitStatus = plot_each_cell(myCell, xlabel, ylabel, imp, IncDict,howInc,NumDict,BoolDict, ScreenConfig, i+1, CellNumber)
        if ExitStatus == 'CANCEL':
            if i > 0: i -= 1
            else: i = 0
        elif ExitStatus == 'EXIT':
            IJ.log('Closed without saving.')
            return 0
        else:
            i += 1
            if ExitStatus == 'EDIT':
                j+=1

    # Save the cells
    Cells.save_cells(myCells, rm=None, ResultsRoot=ResultsRoot, SaveData=True, Prefix='0')
    IJ.log(str(CellNumber) + ' cells were reviewed.')
    IJ.log(str(j) + ' cells were manually edited.')
run()
