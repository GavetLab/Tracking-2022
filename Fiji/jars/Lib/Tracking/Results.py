import os
import csv
import glob


######################################
## Paths to images and results
######################################

def get_rootpath(tif_file):
    # Root > Channel > *.TIF
    return tif_file.split(os.sep + 'w')[0]

def results_root(Root):
    # Data > ... > Root > Channel > *.TIF
    # Results > ... > ResultsRoot
    ResultsRoot = Root.replace(os.sep + 'Data' + os.sep, os.sep + 'Results' + os.sep + 'RAW' + os.sep)
    if not os.path.isdir(ResultsRoot):
        os.makedirs(ResultsRoot)
    return ResultsRoot

######################################
## RoiManager
######################################

def save_rois(RM, ResultsRoot, Name):
    Name += '_ROI.zip'
    FullPath = os.path.join(ResultsRoot, Name)
    RM.runCommand('Deselect')
    RM.runCommand('Save', FullPath)

def load_rois(RM, ResultsRoot, Prefix=None, Type='Nuclei'):
    # Look for all files ending in '*_ROI.zip' and take the last found file
    # Unless Prefix is provided
    if Prefix:
        FullPath = os.path.join(ResultsRoot, Prefix + '_' + Type + '_ROI.zip')
    else:
        os.chdir(ResultsRoot)
        ROIfiles = glob.glob('*_' + Type + '_ROI.zip')
        FullPath = os.path.join(ResultsRoot, ROIfiles[-1])
    RM.runCommand('Open', FullPath)

######################################
## Data table
######################################

def write_tsv(Table, SavePath, Fields):
    # It will overwrite the original tsvfile if it exists!
    # SavePath should point to the tsv file (not to is folder)
    tsvfile = open(SavePath, 'w')
    writer = csv.DictWriter(tsvfile, fieldnames=Fields, dialect='excel-tab')
    DictField = {}
    for Field in Fields:
        DictField[Field] = Field
    writer.writerow(DictField)
    for row in Table:
        filteredrow = dict((k,v) for k,v in row.iteritems() if k in Fields)
        writer.writerow(filteredrow)
    tsvfile.close()

def append_rows(NewRows, SavePath, Fields):
    # SavePath should point to the tsv file
    Table = []
    if os.path.isfile(SavePath):
        tsvfile = open(SavePath, 'r')
        reader = csv.DictReader(tsvfile, dialect='excel-tab')
        for row in reader:
            Table.append(row)
        tsvfile.close()
    Table.extend(NewRows)
    write_tsv(Table, SavePath, Fields)

def read_tsv(SavePath):
    # SavePath should point to the tsv file (not to its folder)
    Table = []
    if os.path.isfile(SavePath):
        tsvfile = open(SavePath, 'r')
        reader = csv.DictReader(tsvfile, dialect='excel-tab')
        for row in reader:
            Table.append(row)
        tsvfile.close()
    return Table

def autoload_tsv(ResultsRoot, FileName=None):
    # Load the latest .tsv file in ResultsRoot folder
    # Unless FileName is provided
    if FileName:
        FullPath = os.path.join(ResultsRoot, FileName)
    else:
        os.chdir(ResultsRoot)
        TSVfiles = glob.glob('*Table.tsv')
        FullPath = os.path.join(ResultsRoot, TSVfiles[-1])
    Table = []
    if os.path.isfile(FullPath):
        tsvfile = open(FullPath, 'r')
        reader = csv.DictReader(tsvfile, dialect='excel-tab')
        for row in reader:
            Table.append(row)
        tsvfile.close()
    return Table
