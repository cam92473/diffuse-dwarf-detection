import argparse
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from scipy.spatial import cKDTree
from ALGORITHM.algorithm import detect_dwarfs
from artificial_dwarf.generate_parameters.generate_parameters import generate_parameters
from artificial_dwarf.insert_dwarf import insert_dwarf_intoarray

def print_progress_bar (iteration, total, prefix = ''):
    percent = 100 * (iteration / float(total))
    length = 40
    filledLength = int(length * iteration // total)
    bar = '█' * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent:.0f}% complete', end = '\r')
    if iteration == total: 
        print("\n")

num_trials = 100

mag, reff, n, q, theta = generate_parameters(num_dwarfs=num_trials,display=True)

'''mag = [21]
reff = [20.]
n = [0.7]
q = [0.7]
theta = [45.]'''

signature = 'montecarlo'

with fits.open('artificial_dwarf/psf/t4_dw2_g_psf.fits') as hdul:
    psf = hdul[0].data

completeness = np.zeros(num_trials)

for i in range(num_trials):

    print(f"working on point {i}...")

    with fits.open('input_images/tiles/tile4/g/tile4cut_g.fits') as hdul:
        data = hdul[0].data
        header = hdul[0].header

    #valid_dw_coords = np.load('TRAIN_CNN/authentic_dataset/dwarf_placement_mask/total_mask.npy')
    valid_dw_coords = np.load('TRAIN_CNN/authentic_dataset/dwarf_placement_mask/outer_mask.npy')

    num_injected_dw = 1000

    injected_coords = np.zeros((num_injected_dw,2))
    j = 0
    while j < num_injected_dw:
        r, c = np.random.randint(0,data.shape[0]), np.random.randint(0,data.shape[1])
        if valid_dw_coords[r,c]:
            injected_coords[j] = [r,c]
            valid_dw_coords[int(r-3*reff[i]):int(r+3*reff[i]),int(c-3*reff[i]):int(c+3*reff[i])] = False
            data = insert_dwarf_intoarray(data,psf,mag[i],reff[i],n[i],q[i],theta[i],c,r,return_Ieff=False)
            print_progress_bar(j,num_injected_dw-1,prefix=f'Dwarf {j+1}/{num_injected_dw}')
            j += 1

    fits.writeto('input_images/created_images/raw_images/tile4/artificial/tile4cut_g_injected.fits',data,header,overwrite=True)

    detect_dwarfs('input_images/created_images/raw_images/tile4/artificial/tile4cut_g_injected.fits','input_images/tiles/tile4/g/tile4cut_g_weight.fits', 30, [500,3], signature=signature)

    master_catalog = pd.read_csv(f'ALGORITHM/SKYCOORD_MASTER_CATALOG/master_catalogs/{signature}/{signature}_master_catalog.csv')

    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']
    detected_coords = np.zeros((len(master_catalog),2))
    for k in range(len(master_catalog)):
        ra, dec = master_catalog.iloc[k,0], master_catalog.iloc[k,1]
        x, y = SkyCoord(ra,dec,unit="deg").to_pixel(wcs)
        detected_coords[k] = [y,x]

    tol = 10
    tree = cKDTree(detected_coords)
    matches = tree.query_ball_point(injected_coords,tol)
    matched = np.array([len(match) > 0 for match in matches])
    completeness[i] = np.sum(matched)/num_injected_dw

np.save('605plot/magA',mag)
np.save('605plot/reffA',reff)
np.save('605plot/nA',n)
np.save('605plot/qA',q)
np.save('605plot/thetaA',theta)
np.save('605plot/completenessA',completeness)


            
