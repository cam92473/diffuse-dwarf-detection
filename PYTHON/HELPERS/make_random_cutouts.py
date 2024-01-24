from dwarf_cutout import dwarf_cutout
from artificial_dwarf3 import artificial_dwarf
from numpy.random import randint
from pathlib import Path
import subprocess
from tempfile import mkstemp
from shutil import move, copymode
from os import fdopen, remove
import numpy as np

def replace(inputimage,outputimage,segmap,dwfolder,dwname):
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(dwfolder/'{}.fitting'.format(dwname)) as old_file:
            lines = old_file.readlines()
            for line in lines:
                if line[0:2] == 'A)':
                    line = 'A) {}       # Input data image (FITS file)\n'.format(inputimage)
                elif line[0:2] == 'B)':
                    line = 'B) {}       # Output data image block\n'.format(outputimage)
                elif line[0:2] == 'F)':
                    line = 'F) {}       # Bad pixel mask (FITS image or ASCII coord list)\n'.format(segmap)
                new_file.write(line)
    #Copy the file permissions from the old file to the new file
    copymode(dwfolder/'{}.fitting'.format(dwname), abs_path)
    #Remove original file
    remove(dwfolder/'{}.fitting'.format(dwname))
    #Move new file
    move(abs_path, dwfolder/'{}.fitting'.format(dwname))

image = 'rectangular_region.fits'
weight = 'rectangular_region.weight.fits'
width = 833
height = 833

cwd = Path.cwd()
sex_dir = cwd/'sextractor'

num_dwarftypes = 16
num_samples = 200

dwnames = ['dw1312-4246',\
            'dw1312-4244',\
            'dw1312-4218',\
            'dw1313-4246',\
            'dw1313-4211',\
            'dw1313-4214',\
            'dw1314-4204',\
            'dw1314-4230',\
            'dw1314-4142',\
            'dw1315-4232',\
            'dw1315-4309',\
            'dw1316-4224',\
            'dw1317-4255',\
            'dw1318-4233',\
            'dw1319-4203',\
            'KK98a189']

dwparamsets = np.array([[18.7593,26.9924,1.6347,0.7793,26.8008],\
                    [20.2607,21.2108,0.5433,0.7160,-76.8117],\
                    [21.2324,19.4568,0.6518,0.9359,23.7664],\
                    [20.3224,19.5119,1.24,0.6055,56.5054],\
                    [18.4885,38.5528,0.9490,0.6368,29.4091],\
                    [18.7802,32.5196,0.9574,0.7476,88.0849],\
                    [19.1813,16.2517,1.0157,0.7614,-14.3635],\
                    [19.3542,21.8218,0.9841,0.6604,-65.9851],\
                    [20.3020,15.6003,0.8417,0.5377,-63.0389],\
                    [19.5772,26.1371,1.2355,0.5740,-13.8279],\
                    [21.1714,20.2581,0.3664,0.8138,-41.0798],\
                    [17.7702,66.8451,2.3061,0.8050,52.7319],\
                    [19.7031,45.2936,0.2422,0.9007,25.9168],\
                    [19.4690,52.8630,0.4916,0.9256,-25.1903],\
                    [19.1197,18.0295,0.4510,0.7391,61.3960],\
                    [17.4035,57.8985,0.8001,0.8804,-41.1224]])


for d in range(num_dwarftypes):
    dwname = dwnames[d]
    dwparamset = dwparamsets[d]
    dwfolder = cwd/dwname
    dwtable = dwfolder/(dwname+'.table')

    with open(dwtable,'w') as table:
        line = '#dwarf' + '\t\t\t\t\t' + 'id' + '\t\t\t' + 'gmag' + '\t\t\t' + 'reff' + '\t\t\t' + 'n' + '\t\t\t\t' + 'q' + '\t\t\t\t' + 'theta' + '\t\t\t' + 'chi2'
        table.write(line)
        table.write('\n')

        for s in range(num_samples):
            coords_acceptable = False
            forbidden_regions = np.array([[15202,1348,16375,2533],[15452,0,16625,1080],[14418,3817,15508,4928],[18888,3330,20164,4700],[14736,10384,15630,11296]])
            while not coords_acceptable:
                x = randint(450,20000)
                y = randint(450,16800)
                coords_acceptable = True
                for region in forbidden_regions:
                    if region[0] < x < region[2] or region[1] < y < region[3]:
                        coords_acceptable = False

            imagedwarfname = "dw_{}_{}".format(x,y)
            imagedwarfnamefits = imagedwarfname + '.fits'
            weightdwarfname = "dw_{}_{}_weight".format(x,y)
            weightdwarfnamefits = weightdwarfname + '.fits'
            segdwarfnamefits = imagedwarfname + '_segmap.fits'
            artidwarfname = imagedwarfname + '_artificial'
            artidwarfnamefits = imagedwarfname + '_artificial.fits'
            modeldwarfnamefits = imagedwarfname + '_MODEL.fits'
            psfname = "{}_psf.fits".format(dwname)

            dwarf_cutout(image, "{} {}".format(x,y), width, height, dwfolder/'200dwarfs'/imagedwarfname)

            dwarf_cutout(weight, "{} {}".format(x,y), width, height, dwfolder/'200dwarfs'/weightdwarfname)

            subprocess.call("source-extractor {} -c 200dwarfs.sex -WEIGHT_IMAGE {} -CHECKIMAGE_NAME {}".format(dwfolder/'200dwarfs'/imagedwarfnamefits,dwfolder/'200dwarfs'/weightdwarfnamefits,dwfolder/'200dwarfs'/segdwarfnamefits),shell=True,cwd=sex_dir)

            artificial_dwarf(dwfolder/'200dwarfs'/imagedwarfnamefits,dwfolder/psfname,dwparamset[0],dwparamset[1],dwparamset[2],dwparamset[3],dwparamset[4],417,417,False,dwfolder/'200dwarfs'/artidwarfname)

            replace('200dwarfs/{}'.format(artidwarfnamefits),'200dwarfs/{}'.format(modeldwarfnamefits),'200dwarfs/{}'.format(segdwarfnamefits),dwfolder,dwname)

            subprocess.call("galfit {}.fitting".format(dwname),shell=True,cwd=dwfolder)

            with open(dwfolder/'fit.log') as log:
                bad_fit = False
                lines = log.readlines()
                params = lines[-8].split()

                for el in params:
                    if '*' in el:
                        bad_fit = True
                        break
                
                if bad_fit:
                    gmag = 'NaN'
                    reff = 'NaN'
                    n = 'NaN'
                    q = 'NaN'
                    theta = 'NaN'
                    chi2 = 'NaN'
                else:
                    gmag = params[5]
                    reff = params[6]
                    n = params[7]
                    q = params[8]
                    theta = params[9]
                    chi2 = (lines[-3].split())[2]

            line = imagedwarfname + '\t\t\t' + str(s+1) + '\t\t\t' + gmag + '\t\t\t' + reff  + '\t\t\t' + n + '\t\t\t' + q + '\t\t\t' + theta + '\t\t\t' + chi2
            table.write(line)
            table.write('\n')
