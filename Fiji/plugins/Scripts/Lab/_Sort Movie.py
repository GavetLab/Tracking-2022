from ij import IJ
import os
import glob

def metamorph_parse(tiffname):
    filename = tiffname[0:-4] #to remove the '.tif' at the end
    head, tail = os.path.split(filename)
    fields = tail.split('_')
    Name = fields.pop(0)
    Time = None
    Channel = None
    Pos = '1'
    for field in fields:
        if field[0] == 'w':
            Channel = field
        if field[0] == 's':
            Pos = field[1:]
        if field[0] == 't':
            Time = field[1:]
    return Name, Channel, Pos, Time

#def metasort(File, Name, Channel, Pos, Time):
#    # Sort .tif files into the Data folder
#    head, tail = os.path.split(File)
#    if Time: # Timelapse
#        NewPath = os.path.join('Data', Pos, Channel, tail)
#    else: # Snapshots
#        NewPath = os.path.join('Data', Name, Channel, tail)
#    print NewPath
#    os.renames(File,NewPath)

def metasort(File, Name, Channel, Pos, Time):
    # Sort .tif files into the Data folder
    head, tail = os.path.split(File)
    if Time: # Timelapse
        NewPath = os.path.join('Data', Pos)
    else: # Snapshots
        NewPath = os.path.join('Data', Name, Pos)
    if Channel:
        NewPath = os.path.join(NewPath, Channel)
    NewPath = os.path.join(NewPath, tail)
    os.renames(File,NewPath)

def protocols_sort(Root):
    # Sort .txt, .nd and .STG files into the Protocols folder
    os.chdir(Root)
    filetypes = ['*.txt', '*.nd', '*.STG']
    for filetype in filetypes:
        FileList = glob.glob(filetype)
        if FileList:
            for File in FileList:
                os.renames(File, os.path.join('Protocols', File))

def run():
    Root = IJ.getDir('')
    os.chdir(Root)
    Filelist = glob.glob('*.TIF')
    for File in Filelist:
        Name, Channel, Pos, Time = metamorph_parse(File)
        metasort(File, Name, Channel, Pos, Time)
    protocols_sort(Root)


run()
