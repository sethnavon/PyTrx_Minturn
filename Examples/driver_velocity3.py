# -*- coding: utf-8 -*-
'''
PyTrx (c) by Penelope How, Nick Hulton, Lynne Buie

PyTrx is licensed under a
Creative Commons Attribution 4.0 International License.

You should have received a copy of the license along with this
work. If not, see <http://creativecommons.org/licenses/by/4.0/>.


PYTRX EXAMPLE DENSE VELOCITY DRIVER (EXTENDED VERSION)

This script is part of PyTrx, an object-oriented programme created for the 
purpose of calculating real-world measurements from oblique images and 
time-lapse image series.

This driver calculates surface velocities using modules in PyTrx at Kronebreen,
Svalbard, for a subset of the images collected during the 2014 melt season. 
Specifically this script performs feature-tracking through sequential daily 
images of the glacier to derive surface velocities (spatial average, 
individual point displacements and interpolated velocity maps) which have been 
corrected for image distortion and motion in the camera platform (i.e. image
registration).

This script is a class-independent version of 'driver_velocity1.py'. 
The functions used here do not depend on class object inputs and can be run as 
stand-alone functions.

This script has been included in order to provide the user with a more detailed 
overview of PyTrx's functionality beyond its object-oriented structure. It also 
allows flexible intervention and adaptation where needed. 
'''

#Import packages
import sys
import numpy as np
import cv2
import glob
import cv2
import math
import time
from scipy.sparse import lil_matrix
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
from pathlib import Path

#Import PyTrx packages
sys.path.append('../')
from CamEnv import setProjection, projectXYZ, getRotation, optimiseCamera
from Velocity import calcDenseHomography, calcSparseHomography, calcDenseVelocity, readDEMmask
from DEM import load_DEM
import FileHandler
import Utilities 
 
#------------------------   Define inputs/outputs   ---------------------------

print('\nDEFINING DATA INPUTS')

#Camera name, location (XYZ) and pose (yaw, pitch, roll)
camname = 'KR2_2014'
camloc = np.array([447948.820, 8759457.100, 407.092])

#campose = np.array([4.80926, 0.05768, 0.14914]) 
campose = np.array([4.80926, 0.05768, 0.14914]) 


#Define image folder and image file type for velocity tracking
imgFiles = '../Examples/images/KR2_2014_subset/*.JPG'

#Define calibration images and chessboard dimensions (height, width)
calibPath = '../Examples/camenv_data/calib/KR1_2014_1.txt'

#Load DEM from path
DEMpath = '../Examples/camenv_data/dem/KR_demsmooth.tif'        

#Define masks for velocity and homography point generation
vmaskPath = '../Examples/camenv_data/masks/KR2_2014_dem_vmask.jpg'      
hmaskPath = '../Examples/camenv_data/invmasks/KR2_2014_inv.jpg'    

#Define reference image (where GCPs have been defined)
refimagePath = '../Examples/camenv_data/refimages/KR2_2014.JPG'

#Define GCPs (world coordinates and corresponding image coordinates)
GCPpath = '../Examples/camenv_data/gcps/KR2_2014.txt'


print('\nDEFINING DATA OUTPUTS')

#Velocity output
target1 = '../Examples/results/velocity3/velo_output.csv'

#Homography output
target2 = '../Examples/results/velocity3/homography.csv'

#Shapefile output (with WGS84 projection)
target3 = '../Examples/results/velocity3/shpfiles/'     
projection = 32633

#Plot outputs
target4 = '../Examples/results/velocity3/imgfiles/'
interpmethod='linear'                                 #nearest/cubic/linear
cr1 = [445000, 452000, 8754000, 8760000]              #DEM plot extent   


#--------------------------   Define parameters   -----------------------------

#DEM parameters 
DEMdensify = 2                      #DEM densification factor (for smoothing)

#Image enhancement paramaters
band = 'L'                          #Image band extraction (R, B, G, or L)
equal = True                        #Histogram equalisation?

#Velocity parameters
vwin = (25,25)                      #Tracking window size
vback = 1.0                         #Back-tracking threshold  
vmax = 50000                        #Maximum number of points to seed
vqual = 0.1                         #Corner quality for seeding
vmindist = 5.0                      #Minimum distance between seeded points
vminfeat = 4                        #Minimum number of seeded points to track
                           
#Homography parameters
hwin = (25,25)                      #Stable pt tracking window size
hmethod = cv2.RANSAC                #Homography calculation method 
                                    #(cv2.RANSAC, cv2.LEAST_MEDIAN, or 0)
hreproj = 5.0                       #Maximum allowed reprojection error
hback = 0.5                         #Back-tracking threshold
herr = True                         #Calculate tracking error?
hmax = 50000                        #Maximum number of points to seed
hqual = 0.5                         #Corner quality for seeding
hmindist = 5.0                      #Minimum distance between seeded points
hminfeat = 4                        #Minimum number of seeded points to track


#----------------------   Set up camera environment   -------------------------

print('\nLOADING DEM')
dem = load_DEM(DEMpath)
dem=dem.densify(DEMdensify)


print('\nLOADING GCPs')
GCPxyz, GCPuv = FileHandler.readGCPs(GCPpath)


print('\nLOADING CALIBRATION')
calib_out = FileHandler.readMatrixDistortion(calibPath)
matrix1=np.transpose(calib_out[0])                           #Get matrix
tancorr = calib_out[1]                                      #Get tangential
radcorr = calib_out[2]                                      #Get radial
focal = [matrix1[0,0], matrix1[1,1]]                          #Focal length
camcen = [matrix1[0,2], matrix1[1,2]]                         #Principal point
 

print('\nLOADING IMAGE FILES')
imagelist = sorted(glob.glob(imgFiles))
im1 = FileHandler.readImg(imagelist[0], band, equal)
imn1 = Path(imagelist[0]).name


print('\nOPTIMISING CAMERA ENVIRONMENT')
projvars = [camloc, campose, radcorr, tancorr, focal, camcen, refimagePath] 
new_projvars = optimiseCamera('YPR', projvars, GCPxyz, GCPuv, optmethod='trf', 
                              show=True)


print('\nCOMPILING TRANSFORMATION PARAMETERS')
camloc1, campose1, radcorr1, tancorr1, focal1, camcen1, refimagePath = new_projvars

matrix2 = np.array([focal1[0], 0, camcen[0], 0, focal1[1], 
                   camcen[1], 0, 0, 1]).reshape(3,3)

distort = np.hstack([radcorr1[0][0], radcorr1[0][1],          #Compile distortion
                     tancorr1[0][0], tancorr1[0][1],          #parameters
                     radcorr1[0][2]])

invprojvars = setProjection(dem, camloc, campose, 
                            radcorr, tancorr, focal, 
                            camcen, refimagePath)          #Inverse projection
 
new_invprojvars = setProjection(dem, camloc1, campose1, 
                            radcorr1, tancorr1, focal1, 
                            camcen1, refimagePath)          #Inverse projection

campars = [dem, new_projvars, new_invprojvars]                 #Compiled parameters


print('\nLOADING MASKS')
print('Defining velocity mask')
vmask = readDEMmask(dem, im1, invprojvars, vmaskPath)

print('Defining homography mask')
hmask = FileHandler.readMask(None, hmaskPath)
#hmask = readDEMmask(dem, im1, invprojvars, hmaskPath)


#--------------------   Plot camera environment info   ------------------------

print('\nPLOTTING CAMERA ENVIRONMENT INFO')

##Load reference image
#refimg = FileHandler.readImg(refimagePath) 
#imn = Path(refimagePath).name

##Show GCPs
#Utilities.plotGCPs([GCPxyz, GCPuv], refimg, imn, 
#                   dem, camloc, extent=None)          

##Show Prinicpal Point in image
#Utilities.plotPrincipalPoint(camcen, refimg, imn)

#Show corrected and uncorrected image

#Utilities.plotCalib(matrix2, distort, refimg, imn)



#----------------------   Calculate velocities   ------------------------------

print('\nCALCULATING VELOCITIES')

#Create empty output variables
velo = []                                     
homog = []

#Cycle through image pairs (numbered from 0)
for i in range(len(imagelist)-1):

    #Re-assign first image in image pair
    im0=im1
    imn0=imn1
                    
    #Get second image (corrected) in image pair
    im1 = FileHandler.readImg(imagelist[i+1], band, equal)
    imn1 = Path(imagelist[i+1]).name                                                       
    
    
    print('\nProcessing images: ' + str(imn0) + ' and ' + str(imn1))
        
#    #Calculate homography between image pair
    print('Calculating homography...')
#    hgrid = [100,100]
#    htemp=30
#    hsearch=100    
#    trmethod='cv2.TM_CCORR_NORMED' 
#    homogmeth=cv2.RANSAC
#    reproj=5.0
#    hmin=4.0
#    hg = calcDenseHomography(im0, im1, hmask, [matrix2,distort], hgrid, htemp, 
#                             hsearch, dem, projvars, trmethod, 
#                             homogmeth, reproj, hmin)   
    

    hg = calcSparseHomography(im0, im1, hmask, [matrix2,distort], hmethod, hreproj, 
                              hwin, hback, hminfeat, [hmax, hqual, hmindist])
    homog.append(hg)
                             
    #Calculate velocities between image pair
    print('Calculating velocity...')
    
    griddistance = [500,500]
    templatesize=30
    searchsize=100    
    method='cv2.TM_CCORR_NORMED'  
    threshold=2.0
    min_features=4.0

    vl = calcDenseVelocity(im0, im1, griddistance, method, templatesize, 
                           searchsize, vmask, [matrix2,distort], 
                           [hg[0],hg[3]], campars, threshold)   

#    vl = calcDenseVelocity(im0, im1, griddistance, method, templatesize, 
#                           searchsize, demmask, None, None, campars, threshold)  
    velo.append(vl)             

#---------------------------  Export data   -----------------------------------

print('\nWRITING DATA TO FILE')

#Get all image names
names=[]
for i in imagelist:
    names.append(Path(i).name)

#Extract xyz velocities, uv velocities, and xyz0 locations
xyzvel=[item[0][0] for item in velo] 
xyzerr=[item[0][3] for item in velo]
uvvel=[item[1][0] for item in velo]
xyz0=[item[0][1] for item in velo]

#Write out velocity data to .csv file
FileHandler.writeVeloFile(xyzvel, uvvel, homog, names, target1) 

#Write homography data to .csv file
FileHandler.writeHomogFile(homog, names, target2)

#Write points to shp file                
FileHandler.writeVeloSHP(xyzvel, xyzerr, xyz0, names, target3, projection)       
#
#
#----------------------------   Plot Results   --------------------------------

print('\nPLOTTING OUTPUTS')

#Extract uv0, uv1corr, xyz0 and xyz1 locations 
uv0=[item[1][1] for item in velo]
uv1corr=[item[1][2] for item in velo]
uverr=[item[1][4] for item in velo]
xyz0=[item[0][1] for item in velo]
xyz1=[item[0][2] for item in velo]


#Cycle through data from image pairs   
for i in range(len(xyz0)):
    
    #Get image from sequence
    im=FileHandler.readImg(imagelist[i], band, equal)

    #Correct image for distortion
    newMat, roi = cv2.getOptimalNewCameraMatrix(matrix2, distort, 
                                                (im.shape[1],im.shape[0]), 
                                                1, (im.shape[1],im.shape[0])) 
    im = cv2.undistort(im1, matrix2, distort, newCameraMatrix=newMat)
    
    #Get image name
    imn = Path(imagelist[i]).name
    print('Visualising data for ' + str(imn))
        
    #Plot uv velocity points on image plane  
    Utilities.plotVeloPX(uvvel[i], uv0[i], uv1corr[i], im, show=True, 
                         save=None)

#    Utilities.plotVeloPX(uverr[i], uv0[i], uv1corr[i], im, show=True, 
#                         save=target4+'uverr_'+imn)
#    
#    uvsnr=uverr[i]/uvvel[i]
#    Utilities.plotVeloPX(uvsnr, uv0[i], uv1corr[i], im, show=True, 
#                         save=target4+'uvsnr_'+imn)    


    #Plot xyz velocity points on dem  
    Utilities.plotVeloXYZ(xyzvel[i], xyz0[i], xyz1[i], dem, show=True, 
                          save=None)

#    Utilities.plotVeloXYZ(xyzerr[i], xyz0[i], xyz1[i], dem, show=True, 
#                          save=target4+'xyzerr_'+imn)    
                
#    #Plot interpolation map
#    grid, pointsextent = Utilities.interpolateHelper(xyzvel[i], xyz0[i], 
#                                                     xyz1[i], interpmethod)
#    Utilities.plotInterpolate(grid, pointsextent, dem, show=True, 
#                              save=target4+'interp_'+imn)  

    
#------------------------------------------------------------------------------
print('\nFinished')