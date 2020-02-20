
import os
import pydicom
import numpy as np
import math
import sys   # for error handling
import struct # to unpack dicom private tag
from operator import itemgetter, attrgetter 
from collections import defaultdict
from struct import unpack as unpack


def try_dicom(fullPath):
    "return pydicom handler if read sucess, else return None"
    if os.path.isfile(fullPath):
        try:
            ds = pydicom.dcmread(fullPath,stop_before_pixels=True)
            return ds
        except:
            print(fullPath + " is not a valid dicom")
            return None
        
def is_centerline_dicom(pydicomData):
    "test if it is ISP private centerline dicom"
    if ( [0x0020,0x4000] in pydicomData and ([0x07a1,0x1012] in pydicomData)):
        #has comment tag(00204,000) or no centerline data (07a1, 1012)
        return True
    else:
        return False

def exportCenterline(filePath):
    ds = try_dicom(filePath)
    if ( [0x0020,0x4000] in ds and ([0x07a1,0x1012] in ds)):
        cur_dir = os.path.dirname(filePath)
        findingName = ds[0x0020,0x4000].value
        centerlineData = ds[0x07a1,0x1012].value
        #centerlineArray = struct.unpack("f"*(len(centerlineData)//4), centerlineData).reshape(-1,9)[:,0:3]
        if ds[0x07a1,0x1012].VR == "UN":
            ds[0x07a1,0x1012].VR = "FL"
            ds[0x07a1,0x1012].value = unpack("f"*(len(ds[0x07a1,0x1012].value)//4), ds[0x07a1,0x1012].value)
        centerlineArray = np.array(ds[0x07a1,0x1012].value).reshape(-1,9)[:,0:3]
        optName = findingName + " centerline.dat"
        outputPath = os.path.join(cur_dir, optName)
        
        fid = ds[0x0020,0x0052].value        
        referencedObjectUID = ds[0x01E1,0x1046].value 
        referencedObjectUID = str(referencedObjectUID[51:])          
        rend = referencedObjectUID.find('_')
        fs = open(outputPath, "wt")
        fs.writelines(ds[0x0020,0x0052].value+"\n")
        fs.writelines(ds[0x0020,0x000D].value+"\n")
        if hasattr(ds, "ReferencedSeriesSequence"):
            fs.writelines(ds.ReferencedSeriesSequence[0].SeriesInstanceUID+"\n")
        else:
            fs.writelines(ds.ReferencedStudySequence[0].ReferencedSOPInstanceUID+"\n")
        fs.writelines(referencedObjectUID[2:rend]+"\n")
        fs.writelines(ds.StudyDate+"\n")
        fs.writelines(ds.StudyTime+"\n")
        fs.writelines(str(findingName)+"\n")
        fs.writelines(str(centerlineArray.shape[0])+"\n")
        for i in range(0,centerlineArray.shape[0]):
            fs.writelines(str(centerlineArray[i,0])+" "+str(centerlineArray[i,1])+" "+str(centerlineArray[i,2])+"\n")
    else:
        return False



# export centerline data in dir to R readable format
def walkthroughForCenterlines():
    root_dir = sys.argv[1]
    skip_axial = True

    print("Root directory: "+ root_dir)
    print("Trying to find all filenames in directory...")

    count=0
    for dirPath, dirNames, fileNames in os.walk(root_dir):
        for f in fileNames:
            count= count+1
    print("A total of "+str(count)+" files found in root directory for analyzing.")
    print("Start analyzing file:")

    i = 1
    for dirPath, dirNames, fileNames in os.walk(root_dir):
        for f in fileNames:
            fullPath = os.path.join(dirPath, f)
            print(str(i) +" / "+ str(count))
            i=i+1
            ds = try_dicom(fullPath)
            if ds != None:
                #condition when ds is a valid dicom
                #next part skips AXIAL in directory
                if (skip_axial == True):
                    
                    if("AXIAL" in ds.ImageType):
                        print("Found Axial images, skipping folder " + fullPath)
                        i = i + len(fileNames) -1
                        break # break to stop this loop, to proceed to next dir.
                    if("PRIMARY" in ds.ImageType):
                        print("Found primary images, skipping folder " + fullPath)
                        i = i + len(fileNames) -1
                        break
                # next part checks for centerline data
                if not is_centerline_dicom(ds):
                    print(fullPath + " has no centerline Tag")
                    continue
                # noe ds is a valid centerline dicom, save its path to list, 

                try:
                    relPath = os.path.relpath(fullPath, root_dir)
                    if not( hasattr(ds, "ReferencedSeriesSequence") or hasattr(ds, "ReferencedStudySequence")):
                        raise AttributeError("no Referenced series or study UID.")
                    print(fullPath +" is a valid centerline dicom")
                    exportCenterline(fullPath)
                except:
                    print(fullPath +" is not a valid centerline dicom:" + str(sys.exc_info()[1]))
                
            else:  
                print(fullPath + " is not a valid dicom")
                continue


walkthroughForCenterlines()