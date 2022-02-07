# -*- coding: utf8 -*-
from ij import IJ
from ij.process import ImageProcessor
from ij.gui import Roi, ShapeRoi, PointRoi

from java.awt import Color as c

import Results
import os
import glob
import math

class Cell:
    TotalCells = 0

    def __init__(self, name=None, Pos=None):
        Cell.TotalCells += 1
        self.number = Cell.TotalCells
        self.Table = []
        # ROIs
        self.Nuclei = []
        self.Cytoplasms = []
        self.FullCells = []
        if not name:
            if Pos:
                self.name = 'Cell' + str(Pos) + str(self.number)
            else:
                self.name = 'Cell' + str(self.number)
        else:
            self.name = name
        self.Fields = ['Name', 'BaseName', 'Slice']

    def __len__(self):
        return len(self.Nuclei)

    ### Append a new Roi to the end of the cell
    def addNucleus(self, Roi):
        i = len(self.Nuclei)
        self.Nuclei.append(Roi)
        if len(self.Table) == i:
            Slice = Roi.getPosition()
            BaseName = self.name + '_t' + str(i)
            CurrentData = {'Slice': Slice, 'Name': self.name, 'BaseName': BaseName}
            self.Table.append(CurrentData)

    def addCytoplasm(self, Roi):
        i = len(self.Cytoplasms)
        self.Cytoplasms.append(Roi)
        if len(self.Table) == i:
            Slice = Roi.getPosition()
            BaseName = self.name + '_t' + str(i)
            CurrentData = {'Slice': Slice, 'Name': self.name, 'BaseName': BaseName}
            self.Table.append(CurrentData)

    def addFullCell(self, Roi):
        i = len(self.FullCells)
        self.FullCells.append(Roi)
        if len(self.Table) == i:
            Slice = Roi.getPosition()
            BaseName = self.name + '_t' + str(i)
            CurrentData = {'Slice': Slice, 'Name': self.name, 'BaseName': BaseName}
            self.Table.append(CurrentData)

    def addBlankLine(self, Slice):
        i = len(self.Nuclei)
        self.Nuclei.append(None)
        if len(self.Table) == i:
            BaseName = self.name + '_t' + str(i)
            CurrentData = {'Slice': Slice, 'Name': self.name, 'BaseName': BaseName}
            self.Table.append(CurrentData)

    ### Table ###
    def editTable(self, DictRow, Index=-1):
        self.Table[Index].update(DictRow)
        Fields = DictRow.keys()
        self.Fields = list(set(self.Fields + Fields))

    def appendEmptyLine(self):
        self.Table.append({})

    def get_occurences(self, String, Column):
        occurences = []
        if Column in self.Fields:
            for i, Row in enumerate(self.Table):
                if Column in Row.keys() and Row[Column] == String:
                    occurences.append(int(float(Row['Slice'])))
        return occurences

    def get_values_in_column(self, Column):
        occurences = []
        if Column in self.Fields:
            for i, Row in enumerate(self.Table):
                if Row[Column]:
                    occurences.append(Row[Column])
        return occurences

    def getRoiAt(self, Slice):
        for i, Row in enumerate(self.Table):
            if int(float(Row['Slice'])) == Slice:
                return self.Nuclei[i]

    def annotate(self, String, Slice, Column, replace=False, add=False):
        if replace: #Starts by removing any occurence of String in Column
            if Column in self.Fields:
                for i, Row in enumerate(self.Table):
                    if Column in Row.keys() and Row[Column] == String:
                        self.Table[i][Column] = ''
        # Add 'string' annotation to the Column field at the slice of choice
        if Slice > self.Table[-1]['Slice']: #TODO won't work, if a blank lower Slice was appended 
            self.addBlankLine(Slice)
        for i, Row in enumerate(self.Table):
            if int(float(Row['Slice'])) == Slice:
                if add and Column in self.Table[i].keys():
                    prevValue = self.Table[i][Column]
                    if prevValue:
                        String = str(prevValue) + ';' + str(String)
                self.Table[i][Column] = String
                self.addField(Column)
                break

    def addField(self, NewField):
        # NewField should be a string
        if NewField not in self.Fields:
            self.Fields.append(NewField)

    def assign_class(self, value):
        # included if value == True
        self.Table[0]['Class'] = value
        self.addField('Class')

    def isIncluded(self):
        if 'Included' in self.Table[0].keys() and self.Table[0]['Included'] == 'True':
            return True
        else:
            return False

    def isExcluded(self):
        if 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            return True
        else:
            return False

    def include_cell(self, value):
        # included if value == True
        for row in self.Table:
            row['Included'] = value
        self.addField('Included')

    def exclude_cell(self, value):
        # excluded if value == True
        for row in self.Table:
            row['Excluded'] = value
        self.addField('Excluded')

    def add_measurements(self, BaseName, Index, ImgStat, Keys, Roi,ip):
        for Key in Keys:
            ## Pixel values
            if Key == 'Mean':
                self.Table[Index][BaseName + ' Mean'] = ImgStat.mean
                self.addField(BaseName + ' Mean')
            elif Key == 'Median':
                self.Table[Index][BaseName + ' Median'] = ImgStat.median
                self.addField(BaseName + ' Median')
            elif Key == 'Min':
                self.Table[Index][BaseName + ' Min'] = ImgStat.min
                self.addField(BaseName + ' Min')
            elif Key == 'Max':
                self.Table[Index][BaseName + ' Max'] = ImgStat.max
                self.addField(BaseName + ' Max')
            elif Key == 'StD':
                self.Table[Index][BaseName + ' StD'] = ImgStat.stdDev
                self.addField(BaseName + ' StD')
            ## Histogram shape
            elif Key == 'Kurtosis':
                self.Table[Index][BaseName + ' Kurtosis'] = ImgStat.kurtosis
                self.addField(BaseName + ' Kurtosis')
            elif Key == 'Skewness':
                self.Table[Index][BaseName + ' Skewness'] = ImgStat.skewness
                self.addField(BaseName + ' Skewness')
            ## Roi Shape
            elif Key == 'Area':
                self.Table[Index]['Area'] = ImgStat.area
                self.addField('Area')
            elif Key == 'Perimeter':
                self.Table[Index]['Perimeter'] = Roi.getLength()
                self.addField('Perimeter')
            elif Key == 'Circularity':
                area = ImgStat.area
                perim = Roi.getLength()
                circ = 4*math.pi*float(area)/(float(perim)**2)
                self.Table[Index]['Circularity'] = circ
                self.addField('Circularity')
            elif Key == 'Centroid':
                self.Table[Index]['xCentroid'] = ImgStat.xCentroid
                self.addField('xCentroid')
                self.Table[Index]['yCentroid'] = ImgStat.yCentroid
                self.addField('yCentroid')
            elif Key == 'Feret':
                Feret, Angle, MinFeret, FeretX, FeretY = Roi.getFeretValues()
                self.Table[Index]['FeretDiam'] = Feret
                self.addField('FeretDiam')
                self.Table[Index]['FeretAngle'] = Angle
                self.addField('FeretAngle')
                self.Table[Index]['MinFeret'] = MinFeret
                self.addField('MinFeret')
                self.Table[Index]['FeretX'] = FeretX
                self.addField('FeretX')
                self.Table[Index]['FeretY'] = FeretY
                self.addField('FeretY')
            ## Percentiles
            elif Key == '1st & 99th percentiles':
                FirstPerc, LastPerc = FindPercentiles(Roi, ip, (1,99))
                self.Table[Index][BaseName + ' 1%'] = FirstPerc
                self.addField(BaseName + ' 1%')
                self.Table[Index][BaseName + ' 99%'] = LastPerc
                self.addField(BaseName + ' 99%')

    ### Measure cell ###
    def measure_channel(self, imp, ChannelName, Keys, Type):
        ip = imp.getProcessor()
        if Type == 'Nucleus':
            array = self.Nuclei
        elif Type == 'Cytoplasm':
            array = self.Cytoplasms
        elif Type == 'Full Cell':
            array = self.FullCells
        for i, Roi in enumerate(array):
            Slice = self.Table[i]['Slice']
            imp.setPosition(int(Slice))
            ip.setRoi(Roi)
            stat = ip.getStatistics()
            self.add_measurements(ChannelName + ' ' + Type, i, stat, Keys, Roi,ip)

    def FindPercentiles(self, Roi,ip,percentiles):
        PixCoord = Roi.getContainedPoints()
        Pixels = []
        for pixel in PixCoord:
            Value = ip.getPixel(pixel.x,pixel.y) 
            Pixels.append(Value)
        Pixels.sort()
        length = len(Pixels)
        # percentiles to find are stored in an array
        PercIdx = [perc*length/100 for perc in percentiles]
        PercValues = [Pixels[Idx] for Idx in PercIdx]
        return PercValues

    ### Generate cytoplasm  ###
    def NucleiDonut(self, Rings):
        # Get cytoplasm from donut arround nucleus
        from ij.plugin import RoiEnlarger as RE
        def getCytoplasmDonut(Roi):
            MaxRoi = RE.enlarge(Roi, Rings[1])
            MinRoi = RE.enlarge(Roi, Rings[0])
            Donut = ShapeRoi(MaxRoi).xor(ShapeRoi(MinRoi))
            return Donut
        self.Cytoplasms = [] #ensure array is empty
        for Nucleus in self.Nuclei:
            Slice = Nucleus.getPosition()
            Donut = getCytoplasmDonut(Nucleus)
            Donut.setPosition(Slice)
            self.Cytoplasms.append(Donut)

    def SubtractionCyto(self):
        # Substract nucleus from full cell to get cytoplasm
        self.Cytoplasms = [] #ensure array is empty
        for Nucleus, FullCell in zip(self.Nuclei, self.FullCells):
            sNucleus = ShapeRoi(Nucleus)
            sFull = ShapeRoi(FullCell)
            Cytoplasm = sFull.not(sNucleus)
            self.Cytoplasms.append(Cytoplasm)

    ### Measure bg with nth percentile of surrounding rectangle ROI
    def MakeRectangleRoi(self, myRoi, width, height):
        centroid = myRoi.getContourCentroid()
        x, y = centroid[0], centroid[1]
        ## Compute x
        if x < width/2: x = 0
        elif x + width/2 > 1024: x = 1024 - int(width)
        else: x = int(x - width/2)
        ## Compute y
        if y < height/2: y = 0
        elif y + height/2 > 1024: y = 1024 - int(height)
        else: y = int(y - height/2)
        Cropped_Roi = Roi(x, y, width, height)
        return Cropped_Roi

    def percentile_surroundings(self,width, height, imp, n_percent, ChannelName):
        ip = imp.getProcessor()
        array = self.Nuclei
        for i, Roi in enumerate(array):
            Slice = self.Table[i]['Slice']
            imp.setPosition(int(Slice))
            RectRoi = self.MakeRectangleRoi(Roi, width, height)
            npercent_val = self.FindPercentiles(RectRoi, ip, [n_percent])
            self.Table[i][ChannelName + ' bg' + str(n_percent)] = npercent_val[0]
            self.addField(ChannelName + ' bg' + str(n_percent))

    ### Cell foci
    def count_foci(self, FociPerFrame, BaseName, Type):
        if 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            myColor = c.black
        else:
            ColorList = [c.blue, c.green, c.magenta, c.orange, c.pink, c.red, c.yellow]
            CellNumber = self.number%len(ColorList)
            myColor = ColorList[CellNumber]
        if Type == 'Nucleus':
            array = self.Nuclei
        elif Type == 'Cytoplasm':
            array = self.Cytoplasms
        elif Type == 'Full Cell':
            array == self.FullCells
        FociInCell = []
        for i, Roi in enumerate(array):
            Frame = Roi.getPosition()
            CellName = self.Table[i]['BaseName']
            Foci = 0
            j = 0
            k = 1
            while j < len(FociPerFrame[Frame - 1]):
                x, y = FociPerFrame[Frame - 1][j]
                if Roi.contains(x,y):
                    Foci += 1
                    FociPerFrame[Frame - 1].pop(j)
                    FociRoi = PointRoi(x,y)
                    FociRoi.setName(CellName + '_f' + str(k))
                    FociRoi.setPosition(Frame)
                    FociRoi.setPointType(3)
                    FociRoi.setSize(2)
                    FociRoi.setStrokeColor(myColor)
                    k += 1
                    FociInCell.append(FociRoi)
                else:
                    j += 1
            self.Table[i][BaseName + ' count'] = Foci
        self.addField(BaseName + ' count')
        return FociInCell

    #def calcFociStat(FociInt):
    #    # FociInt is the list of all foci intensities in current Roi
    #    MinInt = min(FociInt)
    #    MaxInt = max(FociInt)
    #    SumInt = sum(FociInt) 
    #    return MinInt, MaxInt, SumInt

    #def foci_stat(self, FociPerFrame, FociValues, BaseName, Type):
    #    if Type == 'Nucleus':
    #        array = self.Nuclei
    #    elif Type == 'Cytoplasm':
    #        array = self.Cytoplasms
    #    elif Type == 'Full Cell':
    #        array == self.FullCells
    #    for i, Roi in enumerate(array):
    #        Frame = Roi.getPosition()
    #        Foci = 0
    #        j = 0
    #        FociInt = []
    #        while j < len(FociPerFrame[Frame - 1]):
    #            x, y = FociPerFrame[Frame - 1][j]
    #            if Roi.contains(x,y):
    #                Foci += 1
    #                FociPerFrame[Frame - 1].pop(j)
    #                FociInt.append(FociValues[Frame - 1].pop(j))
    #            else:
    #                j += 1
    #        self.Table[i][BaseName + ' Fcount'] = Foci
    #        if Foci > 0:
    #            MinF,MaxF,SumF = calcFociStat(FociInt)
    #            self.Table[i][BaseName + ' Fmin'] = MinF
    #            self.Table[i][BaseName + ' Fmax'] = MaxF
    #            self.Table[i][BaseName + ' Fsum'] = SumF
    #    self.addField(BaseName + ' Fcount')
    #    self.addField(BaseName + ' Fmin')
    #    self.addField(BaseName + ' Fmax')
    #    self.addField(BaseName + ' Fsum')

    ### Save the cell and display in image
    def addToRM_SG2NEBD(self, RM, Type):
        myColor = c.gray
        if 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            Excluded = True
        else:
            Excluded = False
        if Type == 'Nuclei':
            array = self.Nuclei
        elif Type == 'Cytoplasms':
            array = self.Cytoplasms
        elif Type == 'FullCells':
            array = self.FullCells
        Index = RM.getCount()
        for i, Roi in enumerate(array):
            Name = self.Table[i]['BaseName']
            if self.Table[i]['Phase'] == 'G1-S':
                myColor = c.blue
            if self.Table[i]['Phase'] == 'S-G2':
                myColor = c.red
            if self.Table[i]['Phase'] == 'NEBD':
                myColor = c.green
            if Excluded:
                myColor = c.black
            Roi.setStrokeColor(myColor)
            RM.addRoi(Roi)
            RM.rename(Index, Name)
            Index += 1

    def addToRM_SG2NEBDv2(self, RM, Type):
        if 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            Excluded = True
        else:
            Excluded = False
        if Type == 'Nuclei':
            array = self.Nuclei
        elif Type == 'Cytoplasms':
            array = self.Cytoplasms
        elif Type == 'FullCells':
            array = self.FullCells
        Index = RM.getCount()
        # Find what is in the cell to define what is the initial color
        G1S = self.get_occurences('G1-S', 'Phase')
        SG2 = self.get_occurences('S-G2', 'Phase')
        NEBD = self.get_occurences('NEBD', 'Phase')
        if Excluded:
            myColor = c.black
        elif G1S:
            # True G1-S is blue, cells with at least a G1-S will first be cyan
            myColor = c.cyan
        elif SG2:
            # True S-G2 is red, cells with at least a S-G2 will first be pink
            myColor = c.pink
        elif NEBD:
            # True NEBD is green, cells with at least a NEBD will first be yellow
            myColor = c.yellow
        else:
            # cells with no detected events at all will be gray
            myColor = c.gray
        # Do colors
        for i, Roi in enumerate(array):
            Name = self.Table[i]['BaseName']
            if not Excluded:
                if self.Table[i]['Phase'] == 'G1-S':
                    myColor = c.blue
                elif self.Table[i]['Phase'] == 'S-G2':
                    if NEBD:
                        # Red if NEBD
                        myColor = c.red
                    else:
                        # Magenta if no NEBD
                        myColor = c.magenta
                elif self.Table[i]['Phase'] == 'NEBD':
                    myColor = c.green
            Roi.setStrokeColor(myColor)
            RM.addRoi(Roi)
            RM.rename(Index, Name)
            Index += 1

    def addToRM_SG2NEBDv3(self, RM, Type):
        # only display 'included' cells
        if 'Included' in self.Table[0].keys() and self.Table[0]['Included'] == 'True':
            Included = True
        else:
            Included = False
        if Type == 'Nuclei':
            array = self.Nuclei
        elif Type == 'Cytoplasms':
            array = self.Cytoplasms
        elif Type == 'FullCells':
            array = self.FullCells
        Index = RM.getCount()
        # Find what is in the cell to define what is the initial color
        G1S = self.get_occurences('G1-S', 'Phase')
        SG2 = self.get_occurences('S-G2', 'Phase')
        NEBD = self.get_occurences('NEBD', 'Phase')
        StrokeWidth = 2
        if not Included:
            myColor = c.black
            StrokeWidth = 1
        elif G1S:
            # True G1-S is blue, cells with at least a G1-S will first be cyan
            myColor = c.cyan
        elif SG2:
            # True S-G2 is red, cells with at least a S-G2 will first be pink
            myColor = c.pink
        elif NEBD:
            # True NEBD is green, cells with at least a NEBD will first be yellow
            myColor = c.yellow
        else:
            # cells with no detected events at all will be gray
            myColor = c.gray
        # Do colors
        for i, Roi in enumerate(array):
            Name = self.Table[i]['BaseName']
            if not Excluded:
                if self.Table[i]['Phase'] == 'G1-S':
                    myColor = c.blue
                elif self.Table[i]['Phase'] == 'S-G2':
                    if NEBD:
                        # Red if NEBD
                        myColor = c.red
                    else:
                        # Magenta if no NEBD
                        myColor = c.magenta
                elif self.Table[i]['Phase'] == 'NEBD':
                    myColor = c.green
            Roi.setStrokeColor(myColor)
            Roi.setStrokeWidth(StrokeWidth)
            RM.addRoi(Roi)
            RM.rename(Index, Name)
            Index += 1

    def addToRM_class(self, RM, Type):
        if 'Class' in self.Table[0].keys():
            ColorList = [c.blue, c.green, c.magenta, c.orange, c.pink, c.red, c.yellow]
            ColorNumber = int(self.Table[0]['Class'])%len(ColorList)
            myColor = ColorList[ColorNumber]
        elif 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            myColor = c.black
        else:
            myColor = c.gray
        if Type == 'Nuclei':
            array = self.Nuclei
        elif Type == 'Cytoplasms':
            array = self.Cytoplasms
        elif Type == 'FullCells':
            array = self.FullCells
        Index = RM.getCount()
        for i, Roi in enumerate(array):
            Name = self.Table[i]['BaseName']
            Roi.setStrokeColor(myColor)
            RM.addRoi(Roi)
            RM.rename(Index, Name)
            Index += 1

    def addToRM_included(self, RM, Type):
        if 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            myColor = c.black
        if 'Included' in self.Table[0].keys() and self.Table[0]['Included'] == 'True':
            myColor = c.green
        else:
            myColor = c.gray
        if Type == 'Nuclei':
            array = self.Nuclei
        elif Type == 'Cytoplasms':
            array = self.Cytoplasms
        elif Type == 'FullCells':
            array = self.FullCells
        Index = RM.getCount()
        for i, Roi in enumerate(array):
            Name = self.Table[i]['BaseName']
            Roi.setStrokeColor(myColor)
            RM.addRoi(Roi)
            RM.rename(Index, Name)
            Index += 1

    def addToRM(self, RM, Type):
        if 'Excluded' in self.Table[0].keys() and self.Table[0]['Excluded'] == 'True':
            myColor = c.black
        else:
            ColorList = [c.blue, c.green, c.magenta, c.orange, c.pink, c.red, c.yellow]
            CellNumber = self.number%len(ColorList)
            myColor = ColorList[CellNumber]
        if Type == 'Nuclei':
            array = self.Nuclei
        elif Type == 'Cytoplasms':
            array = self.Cytoplasms
        elif Type == 'FullCells':
            array = self.FullCells
        Index = RM.getCount()
        for i, Roi in enumerate(array):
            Name = self.Table[i]['BaseName']
            Roi.setStrokeColor(myColor)
            RM.addRoi(Roi)
            RM.rename(Index, Name)
            Index += 1

    def fuse_with(self, secondCell):
        # Compare first and last slices
        Slices1 = [int(Slice['Slice']) for Slice in self.Table]
        Slices2 = [int(Slice['Slice']) for Slice in secondCell.Table]
        CommonSlices = list(set(Slices1).intersection(Slices2))
        #if self.Nuclei:
        #if self.Cytoplasms:
        #if self.FullCells:

        if CommonSlices:
            # Va falloir faire un merge des ROIs et des Tables pour ces slices
            # La valeur d'éventuelles mesures sera effacée
            # Seules seront conservées :
            # Name, Basename, Slice 
            for Slice in CommonSlices:
                idx1 = Slices1.index(Slice)
                idx2 = Slices2.index(Slice)




####################################

def load_data(RoiList, ResultsRoot, Exclude=[]):
    CellList = []
    prevName = None
    Index = 0
    TableIndex = 0
    Table = Results.autoload_tsv(ResultsRoot)
    while Index < len(RoiList):
        Roi = RoiList[Index]
        RawName = Roi.getName()
        CellName = RawName.split('_')[0]
        # if CellName is excluded, skip to next
        if CellName in Exclude:
            Index += 1
            continue
        ## Test if current ROI belong to current cell or if new
        if CellName != prevName:
            CellList.append(Cell([Roi]))
            CellList[-1].name = CellName
            prevName = CellName
        elif CellName == prevName:
            CellList[-1].addNext(Roi)
        # Try to find data about current cell in table
        # (even if more cells in table than in RM)
        RoiData = Table[TableIndex]
        if RawName == RoiData['RoiName']:
            CellList[-1].editTable(RoiData)
            TableIndex += 1
        else:
            while RawName != RoiData['RoiName']:
                TableIndex += 1
                RoiData = Table[TableIndex]
            if RawName == RoiData['RoiName']:
                CellList[-1].editTable(RoiData)
                TableIndex += 1
        Index += 1
    return CellList

def load_singlecell_data(CellName, ResultsRoot):
    Index = 0
    prevName = None
    Table = Results.autoload_tsv(ResultsRoot)
    TableLen = len(Table)
    myCell = Cell()
    myCell.name = CellName
    while Index < TableLen:
        SliceData = Table[Index]
        if SliceData['Name'] == CellName:
            myCell.appendEmptyLine()
            myCell.editTable(SliceData)
            prevName = CellName
        elif prevName == CellName:
            return myCell
        Index += 1

def load_cells(ResultsRoot, rm, resetRois=True):
    '''
    Load the ROIs from ResultsRoot and use the associated table
    '''
    # Load the cells and find data from ResultsRoot
    Types = ['Nuclei', 'Cytoplasms', 'FullCells']
    os.chdir(ResultsRoot)
    NucleiZip = glob.glob('*_Nuclei_ROI.zip')
    CytoZip = glob.glob('*_Cytoplasms_ROI.zip')
    FullCellZip = glob.glob('*_FullCells_ROI.zip')
    RoiCount = 0
    # TODO for legacy: as it is now, it won't load all of the '0_ROI_ROI.zip'...
    # Or I could rename all 0_ROI_ROI.zip to 0_Nucleus_ROI.zip
    NucleiRois = None
    CytoRois = None
    FullCellRois = None
    if NucleiZip:
        NucleiZip = os.path.join(ResultsRoot, NucleiZip[-1])
        rm.runCommand('Open', NucleiZip)
        NucleiRois = rm.getRoisAsArray()
        RoiCount = len(NucleiRois)
        DefaultRois = NucleiRois
        if resetRois:
            rm.reset()
    if CytoZip:
        CytoZip = os.path.join(ResultsRoot, CytoZip[-1])
        rm.runCommand('Open', CytoZip)
        CytoRois = rm.getRoisAsArray()
        RoiCount = len(CytoRois)
        DefaultRois = CytoRois
        rm.reset()
    if FullCellZip:
        FullCellZip = os.path.join(ResultsRoot, FullCellZip[-1])
        rm.runCommand('Open', FullCellZip)
        FullCellRois = rm.getRoisAsArray()
        RoiCount = len(FullCellRois)
        DefaultRois = FullCellRois
        rm.reset()
    myCells = []
    prevName = None
    Index = 0
    Table = Results.autoload_tsv(ResultsRoot)
    while Index < RoiCount:
        BaseName = DefaultRois[Index].getName()
        CellName = BaseName.split('_')[0]
        SliceData = Table[Index]
        if CellName != prevName:
            myCells.append(Cell())
            if NucleiRois:
                myCells[-1].addNucleus(NucleiRois[Index])
            if CytoRois:
                myCells[-1].addCytoplasm(CytoRois[Index])
            if FullCellRois:
                myCells[-1].addFullCell(FullCellRois[Index])
            myCells[-1].name = CellName
            prevName = CellName
        elif CellName == prevName:
            if NucleiRois:
                myCells[-1].addNucleus(NucleiRois[Index])
            if CytoRois:
                myCells[-1].addCytoplasm(CytoRois[Index])
            if FullCellRois:
                myCells[-1].addFullCell(FullCellRois[Index])
        if BaseName == SliceData['BaseName']:
            myCells[-1].editTable(SliceData)
        else:
            IJ.log(BaseName + ': Error loading cells from RM')
        Index += 1
    return myCells

def save_cells(Cells, ResultsRoot=None, rm=None, SaveRois=False, SaveData=False, Prefix='', Type='Nuclei', color=''):
    if rm:
        rm.reset()
    FullTable = []
    AllFields = []
    for Cell in Cells:
        if rm:
            if color == 'Phase':
                Cell.addToRM_SG2NEBD(rm, Type)
            elif color == 'Phase v2':
                Cell.addToRM_SG2NEBDv2(rm, Type)
            elif color == 'Phase v3':
                Cell.addToRM_SG2NEBDv3(rm, Type)
            elif color == 'Included':
                Cell.addToRM_included(rm, Type)
            elif color == 'Class':
                Cell.addToRM_class(rm, Type)
            else:
                Cell.addToRM(rm, Type)
        if SaveData and ResultsRoot:
            FullTable.extend(Cell.Table)
            AllFields = list(set(AllFields + Cell.Fields))
    if ResultsRoot:
        if SaveRois:
            Results.save_rois(rm, ResultsRoot, Prefix + '_' + Type)
        if SaveData:
            tsvpath = os.path.join(ResultsRoot, Prefix + '_Table.tsv')
            Results.write_tsv(FullTable, tsvpath, AllFields)
