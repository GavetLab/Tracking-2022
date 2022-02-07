from ij import IJ
from ij.plugin.frame import RoiManager

import Tracking.Results as Results

imp = IJ.getImage()
RM = RoiManager.getInstance()
if not RM:
    RM = RoiManager()
RM.reset()

RM.runCommand("Associate", "true")
RM.runCommand("Centered", "false")
RM.runCommand("UseNames", "true")

# Find where is ResultsRoot for current image
ImgRoot = Results.get_rootpath(IJ.getDir('Image'))
ResultsRoot = Results.results_root(ImgRoot)

# Load cells from ResultsRoot
Results.load_rois(RM, ResultsRoot, Type='Nuclei')
