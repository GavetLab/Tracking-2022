from ij import IJ, ImagePlus, ImageStack
from ij.process import ByteProcessor
from ij.plugin.filter import MaximumFinder
from ij.gui import Wand, PolygonRoi, Roi
from inra.ijpb.watershed import MarkerControlledWatershedTransform2D as MWatershed
from inra.ijpb.binary import BinaryImages
from inra.ijpb.morphology.strel import DiskStrel as Disk
from inra.ijpb.morphology import Morphology

##################### WATERSHED THRESHOLDING (with mask) #########################
def generate_input_bkp(next_imp, method):
    threshold_apply(next_imp, method['input']) 
    input_imp = next_imp.duplicate()
    IJ.run(input_imp, "Invert", "stack")
    return input_imp, next_imp

def generate_mask_bkp(next_imp, method):
    mask_imp = next_imp.duplicate()
    threshold_apply(mask_imp, method['mask'])
    IJ.run(mask_imp, "Invert", "stack")
    return mask_imp, next_imp

def find_markers_bkp(ip, method):
    Maxima = MaximumFinder()
    markerPoly = Maxima.getMaxima(ip, method['markers'], False)
    markers = []
    for x, y in zip(markerPoly.xpoints, markerPoly.ypoints):
        markers.append((x,y))
    return markers

def generate_markerip_bkp(markers, ip):
    marker_ip = ByteProcessor(ip.width, ip.height)
    for i, (x, y) in enumerate(markers):
        marker_ip.set(x,y,i + 1)
    return marker_ip

def segment_frame_bkp(input_ip, mask_ip, marker_ip, method, frame):
    # Find markers
    markers = find_markers(marker_ip, method)
    marker_ip = generate_markerip(markers, marker_ip)
    # Do watershed
    Watershed = MWatershed(input_ip, marker_ip, mask_ip, 4)
    Watershed.setVerbose(False)
    W_ip = Watershed.applyWithPriorityQueueAndDams()
    # Convert each region into a Roi
    myWand = Wand(W_ip)
    RoiInFrame = []
    for x,y in markers:
        if W_ip.get(x,y) != 0: 
            myWand.autoOutline(x, y)
            if len(myWand.xpoints) > 1: #If it's only a single point, ignore it
                myRoi = PolygonRoi(myWand.xpoints, myWand.ypoints, myWand.npoints, Roi.FREEROI)
                myRoi.setPosition(frame)
                RoiInFrame.append(myRoi)
    return RoiInFrame, W_ip, marker_ip

def w_segment_bkp(imp, method):
    IJ.log("Marker controlled watershed:")
    maxFrame = imp.getNSlices()
    # Generate input
    IJ.log(">> Generating input image...")
    input_imp, next_imp = generate_input(imp, method)
    input_ip = input_imp.getProcessor()
    # Generate mask and the image markers will be found on
    IJ.log(">> Generating mask image...")
    mask_imp, marker_imp = generate_mask(next_imp, method)
    mask_ip = mask_imp.getProcessor()
    marker_ip = marker_imp.getProcessor()
    # Find markers and segment each frame using watershed
    IJ.log(">> Flood from local maxima...")
    i = 1
    RoiPerFrames = []
    #W_stack = ImageStack(mask_ip.width, mask_ip.height)
    #Marker_stack = ImageStack(mask_ip.width, mask_ip.height)
    while i <= maxFrame:
        #IJ.log("Frame " + str(i))
        input_imp.setPosition(i)
        mask_imp.setPosition(i)
        marker_imp.setPosition(i)
        RoiInFrame, W_ip, mark_ip = segment_frame(input_ip, mask_ip, marker_ip, method, i)
        #W_stack.addSlice(W_ip)
        #Marker_stack.addSlice(mark_ip)
        RoiPerFrames.append(RoiInFrame)
        i += 1
    #W_imp = ImagePlus('Watershed', W_stack)
    #M_imp = ImagePlus('Markers', Marker_stack)
    #mask_imp.show()
    #input_imp.show()
    #W_imp.show()
    #M_imp.show()
    return RoiPerFrames, input_imp

########### MARKER WATERSHED (no mask, use minimum of img as marker for bg) ##################
UpperArea = 10000

def find_markers(ip, Tolerance):
    Maxima = MaximumFinder()
    markerPoly = Maxima.getMaxima(ip, Tolerance, False)
    markers = []
    for x, y in zip(markerPoly.xpoints, markerPoly.ypoints):
        markers.append((x,y))
    return markers

def generate_markerip(markers, ip):
    marker_ip = ByteProcessor(ip.width, ip.height)
    for i, (x, y) in enumerate(markers):
        marker_ip.set(x,y,i + 1)
    return marker_ip

def find_minimum(ip):
    xmin, ymin = 0,0
    minpix = 65535
    x = 0
    while x < 1024:
        y = 0
        while y < 1024:
            pixelVal = ip.get(x,y)
            if pixelVal < minpix:
                minpix = pixelVal
                xmin = x
                ymin = y
            y += 1
        x += 1
    return xmin,ymin

def segment_frame(input_ip, mask_ip, marker_ip, frame, Tolerance, DiskRadius):
    print frame
    # Find markers
    markers = find_markers(marker_ip, Tolerance)
    # Find minimum marker and prepend it to list of markers (pos 0)
    min_marker = find_minimum(marker_ip)
    markers.insert(0, min_marker)
    marker_ip = generate_markerip(markers, marker_ip)
    # Make contour image
    myDisk = Disk.fromRadius(DiskRadius)
    gradient_ip = Morphology.externalGradient(input_ip, myDisk)
    # Do watershed
    Watershed = MWatershed(gradient_ip, marker_ip, mask_ip, 4)
    Watershed.setVerbose(False)
    W_ip = Watershed.applyWithPriorityQueueAndDams()
    # Convert each region into a Roi
    myWand = Wand(W_ip)
    RoiInFrame = []
    # use magic wand to get the watersheded ROIs
    for x,y in markers: #markers[1:] to remove the background ROI (in pos 0)
        if W_ip.get(x,y) != 0: 
            myWand.autoOutline(x, y)
            if len(myWand.xpoints) > 1: #If it's only a single point, ignore it
                myRoi = PolygonRoi(myWand.xpoints, myWand.ypoints, myWand.npoints, Roi.FREEROI)
                RoiStats = myRoi.getStatistics()
                Area = RoiStats.area
                myRoi.setPosition(frame)
                if Area < UpperArea:
                    RoiInFrame.append(myRoi)
    return RoiInFrame, W_ip

def w_segment(wParam, imp):
    Tolerance = wParam['Tolerance']
    DiskRadius = wParam['DiskRadius']
    InputRB = wParam['InputRB']
    InputSigma = wParam['InputSigma']
    MarkerRB = wParam['MarkerRB']
    MarkerSigma = wParam['MarkerSigma']
    IJ.log("Marker controlled watershed:")
    maxFrame = imp.getNSlices()
    # Generate input
    input_imp = imp.duplicate()
    if InputRB > 0:
        IJ.run(input_imp, "Subtract Background...", "rolling=" + str(InputRB) + " stack")
    IJ.run(input_imp, "Gaussian Blur...", "sigma=" + str(InputSigma) + " stack")
    input_ip = input_imp.getProcessor()
    # Generate mask and the image markers will be found on
    ##TODO generate a mask imp which is a full white 8bit image of same dimensions (except only one frame)
    mask_ip = ByteProcessor(1024, 1024)
    mask_ip.set(255)
    marker_imp = imp.duplicate()
    if MarkerRB > 0:
        IJ.run(marker_imp, "Subtract Background...", "rolling=" + str(MarkerRB) + " stack")
    IJ.run(marker_imp, "Gaussian Blur...", "sigma=" + str(MarkerSigma) + " stack")
    marker_ip = marker_imp.getProcessor()
    # Find markers and segment each frame using watershed
    IJ.log(">> Flood from local maxima...")
    i = 1
    RoiPerFrames = []
    #W_stack = ImageStack(mask_ip.width, mask_ip.height)
    while i <= maxFrame:
        #IJ.log("Frame " + str(i))
        input_imp.setPosition(i)
        marker_imp.setPosition(i)
        RoiInFrame, W_ip = segment_frame(input_ip, mask_ip, marker_ip, i, Tolerance, DiskRadius)
        #W_stack.addSlice(W_ip)
        RoiPerFrames.append(RoiInFrame)
        i += 1
    #W_imp = ImagePlus('Watershed', W_stack)
    #W_imp.show()
    return RoiPerFrames


########### SIMPLE THRESHOLDING ################
def RM_to_RoiPerFrames(RM, MaxFrame):
    UnsortedRois = RM.getRoisAsArray()
    RM.reset()
    SortedRois = [[] for k in range(MaxFrame)]
    for Roi in UnsortedRois:
        SortedRois[Roi.getPosition() - 1].append(Roi)
    return SortedRois

def threshold_apply(imp, method):
    MethodSteps = method.split(' ')
    for field in MethodSteps:
        # Background substraction
        if field[:11] == 'SubstractBg':
            Radius = field[12:]
            IJ.log(">> Rolling Ball " + Radius + "px")
            IJ.run(imp, "Subtract Background...", "rolling=" + Radius + " sliding stack")
        if field[:9] == 'RBnoslide':
            Radius = field[10:]
            IJ.log(">> Rolling Ball " + Radius + "px")
            IJ.run(imp, "Subtract Background...", "rolling=" + Radius + " stack")

        # Filters
        if field[:7] == 'Mexican':
            # https://imagej.nih.gov/ij/plugins/mexican-hat/index.html
            Radius = field[8:]
            IJ.log(">> Mexican Hat filter " + Radius + "px...")
            IJ.run(imp, "Mexican Hat Filter", "radius=" + Radius + " stack")
        if field[:4] == 'Mean':
            Radius = field[5:]
            IJ.log(">> Mean filter " + Radius + "px...")
            IJ.run(imp, "Mean...", "radius=" + Radius + " stack")
        if field[:6] == 'Median':
            Radius = field[7:]
            IJ.log(">> Median filter " + Radius + "px...")
            IJ.run(imp, "Median...", "radius=" + Radius + " stack")
        if field[:8] == 'Gaussian':
            Radius = field[9:]
            IJ.log(">> Gaussian blur " + Radius + "px...")
            IJ.run(imp, "Gaussian Blur...", "sigma=" + Radius + " stack")
        if field[:7] == 'Minimum':
            Value = field[8:]
            IJ.log(">> Minimum " + Value)
            IJ.run(imp, "Min...", "value=" + Value + " stack")
        # Thresholding
        ## Local
        if field[:6] == 'Local_':
            IJ.run(imp, "8-bit", "")
            (Tmethod, Radius) = field[6:].split('_')
            IJ.log(">> Local " + Tmethod + " " + Radius + "px")
            IJ.run(imp, "Auto Local Threshold", "method=" + Tmethod + " radius=" + Radius + " parameter_1=0 parameter_2=0 white stack")
            if imp.isInvertedLut():
                IJ.run(imp, "Invert LUT", "")
        ## Global
        if field[:7] == 'Global_':
            Tmethod = field[7:]
            IJ.log(">> " + Tmethod)
            IJ.run(imp, "Auto Threshold", "method=" + Tmethod + " stack")
            IJ.run(imp, "Invert LUT", "")
            #if imp.isInvertedLut():
            #    IJ.run(imp, "Invert LUT", "")
        ## Manual thresholding
        if field[:7] == 'Manual_':
            Threshold = field[7:]
            IJ.log(">> Manual threshold " + Threshold)
            IJ.setRawThreshold(imp, int(Threshold), 65535, '');
            IJ.run(imp, "Convert to Mask", "method=Default background=Dark");
            if imp.isInvertedLut():
                IJ.run(imp, "Invert LUT", "")
        # Post-treatments
        if field == 'FillHoles':
            IJ.log(">> Fill binary image holes...")
            IJ.run(imp, "Fill Holes", "stack")
        if field == 'Watershed':
            IJ.log(">> Binary Watershed...")
            IJ.run(imp, "Watershed", "stack")
        if field == 'Open':
            IJ.log(">> Binary Open...")
            IJ.run(imp, "Open", "stack")
        # Particle analysis
        if field[:3] == 'PA_':
            (area, circ) = field[3:].split('_')
            IJ.log(">> Particle Analysis: area=" + area + " circ=" + circ)
            IJ.run(imp, "Analyze Particles...", "size=" + area + " circularity=" + circ + " clear add stack")

def toBinary(imp, threshold):
    IJ.setRawThreshold(imp, int(Threshold), 65535, '');
    


def t_segment(orig_imp, method, RM):
    IJ.log("Threshold-based segmentation:")
    imp = orig_imp.duplicate()
    threshold_apply(imp, method)
    MaxFrame = imp.getNSlices()
    RoiPerFrames = RM_to_RoiPerFrames(RM, MaxFrame)
    return RoiPerFrames

##################################################
def segment(imp, myMethod, RM):
    print myMethod
    if 'Watershed' in myMethod['Name']:
        if not myMethod['Method']['Mask']:
            RoiPerFrames = w_segment(myMethod['Method'],imp)
    else:
        RoiPerFrames = t_segment(imp, myMethod['Method'], RM)
    return RoiPerFrames
