# Fiji modules
from ij.process import ByteProcessor
from ij import ImagePlus
from ij.plugin.filter import GaussianBlur
from ij.gui import Wand, PolygonRoi, Roi

# Import watershed from morpholibJ
from inra.ijpb.watershed import MarkerControlledWatershedTransform2D as Watershed
from inra.ijpb.morphology.strel import DiskStrel as Disk
from inra.ijpb.morphology import Morphology

def generate_gradient(ip, sigma):
    myIP = ip.duplicate()
    myBlur = GaussianBlur()
    myBlur.blurGaussian(myIP, sigma)
    myDisk = Disk.fromRadius(sigma)
    gradient_ip = Morphology.externalGradient(myIP, myDisk)
    gradient_ip = Morphology.erosion(gradient_ip, myDisk)
    #TODO: add mexican filter 2px to clean and sharpen the contour image
    return gradient_ip

def generate_marker(markers, ip):
    marker_ip = ByteProcessor(ip.width, ip.height)
    for i, marker in enumerate(markers):
        # Set pixel at marker coordinate to value (i + 1)
        # Not (i) because i can be == 0 (which is the value of bg)
        marker_ip.set(marker[0], marker[1], i + 1)
    return marker_ip

def generate_mask(roi, ip):
    mask_ip = ByteProcessor(ip.width, ip.height)
    mask_ip.setValue(255)
    mask_ip.fill(roi)
    return mask_ip

def split(ip, markers, clusterROI, sigma, input_ip):
    # Generate necessary images
    marker_ip = generate_marker(markers, ip)
    mask_ip = generate_mask(clusterROI, ip)
    if not input_ip:
        input_ip = generate_gradient(ip, sigma)
    # Perform watershed
    myWatershed = Watershed(input_ip, marker_ip, mask_ip, 4)
    myWatershed.setVerbose(False)
    w_ip = myWatershed.applyWithPriorityQueue()
    myWand = Wand(w_ip)
    SplitRois = []
    for marker in markers:
        if clusterROI.contains(marker[0], marker[1]) and w_ip.get(marker[0], marker[1]) != 0:
            myWand.autoOutline(marker[0], marker[1])
            if len(myWand.xpoints) > 1: #If it's only a single point, ignore it
                myRoi = PolygonRoi(myWand.xpoints, myWand.ypoints, myWand.npoints, Roi.FREEROI)
                SplitRois.append(myRoi)
            else:
                SplitRois.append(None)
        else:
            SplitRois.append(None)
    return SplitRois, input_ip
