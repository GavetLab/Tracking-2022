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
# Dictionnaries of features to measure:
ToMeasureNum = {
        "Next S (D1)":[0,0,True,'Next S',0,1],
        "Next S (D2)":[0,0,True,'Next S',1,2],
        "Next G2 (D1)":[0,0,True,'Next G2',0,3],
        "Next G2 (D2)":[0,0,True,'Next G2',1,4],
        "Last frame (D1)":[0,0,True,'Daughter last',0,5],
        "Last frame (D2)":[0,0,True,'Daughter last',1,6],
        }

ToMeasureBool = {
        "D1 lost":[False,False,True,'Daughters Bool','Lost_D1',1],
        "D2 lost":[False,False,True,'Daughters Bool','Lost_D2',2],
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

def getColumn(label, myCell):
    mySerie = []
    for Slice in myCell.Table:
        try:
            val = float(Slice[label])
        except:
            val = 0
        mySerie.append(val)
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

def dialog_with_phase(minX,maxX,NumDict, BoolDict, ScreenConfig):
    # Create dialog asking value for each feature to measure
    gd = NonBlockingGenericDialog('Slice of event')
    NumList = sort_dict(NumDict)
    for Feature in NumList:
        print NumDict[Feature]
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

def doIincludeCell(myCell):
    NEBD = myCell.get_occurences('NEBD', 'Phase')
    isIncluded = myCell.get_occurences('True', 'Included')
    if isIncluded: isIncluded = True
    else: isIncluded = False

    if NEBD and isIncluded:
        return True
    else:
        return False

def makeListOfCells(AllCells):
    SelectedCells = []
    for myCell in AllCells:
        QuantifyCell = doIincludeCell(myCell)
        if QuantifyCell:
            SelectedCells.append(myCell)
    return SelectedCells

def plot_each_cell(myCell, xlabel, ylabel, imp, NumDict,BoolDict,ScreenConfig, CellNum, Total):
    # Get data from cell
    Xdata = getSerie(xlabel, myCell)
    Ydata = getSerie(ylabel, myCell)

    QuantifyCell = doIincludeCell(myCell)
    
    # Get values if already exist

    for Feat in NumDict.keys():
        Values = getColumn(NumDict[Feat][3],myCell)
        offset = NumDict[Feat][4]
        val = int(Values[-1 - offset])
        print Feat, offset, val
        if val:
            NumDict[Feat][0] = val
        else:
            NumDict[Feat][0] = ToMeasureNum[Feat][0]
    for Feat in BoolDict.keys():
        Values = myCell.get_occurences(BoolDict[Feat][4], BoolDict[Feat][3])
        if Values: BoolDict[Feat][0] = True
        else: BoolDict[Feat][0] = ToMeasureBool[Feat][0]
    print NumDict
    
    WindowName = myCell.name +' ('+str(CellNum)+'/'+str(Total)+')'
    myPlot = plot_data(WindowName, xlabel, ylabel, Xdata, Ydata)

    # Annotate plot and mark cell in movie
    SG2time = 0
    NEBDtime = 0
    # Look for S-G2 and NEBD
    G2 = myCell.get_occurences('S-G2', 'Phase')
    NEBD = myCell.get_occurences('NEBD', 'Phase')
    if G2: SG2time = int(G2[0])
    if NEBD: NEBDtime = int(NEBD[0])
    if SG2time != 0:
        drawLine(SG2time, c.red, myPlot)
    if NEBDtime != 0:
        drawLine(NEBDtime, c.green, myPlot)

    if NEBDtime:
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
    print NumDict
    NumDict,BoolDict, Included, Excluded, ExitStatus = dialog_with_phase(0,1000,NumDict, BoolDict, ScreenConfig)

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

            #for Feat in NumDict.keys():
            #    Values = getColumn(NumDict[Feat][3],myCell)
            #    if Values[-1 - NumDict[Feat[4]]]:
            #        NumDict[Feat][0] = int(Values[-1 - NumDict[Feat][4]])
            #    else:
            #        NumDict[Feat][0] = ToMeasureNum[Feat][0]

        for Feat in NumDict.keys():
            prevVal = NumDict[Feat][0]
            newVal = NumDict[Feat][1]
            if prevVal != newVal:
                ColumnName = NumDict[Feat][3]
                myCell.annotate(newVal, max(Xdata) - NumDict[Feat][4], ColumnName, replace=True)
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
    NumDict, BoolDict = dialogSelectMeasure()

    # Load cells to ROI manager
    Cells.save_cells(myCells, rm=RM, Type='Nuclei', color=NucleiColor)
    RM.runCommand(imp,"Show All")

    # Display plot for each cell
    CellList = makeListOfCells(myCells)
    i = 0
    j = 0
    CellNumber = len(CellList)
    while i < CellNumber:
        myCell = CellList[i]
        ExitStatus = plot_each_cell(myCell, xlabel, ylabel, imp,NumDict,BoolDict, ScreenConfig, i+1, CellNumber)
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
