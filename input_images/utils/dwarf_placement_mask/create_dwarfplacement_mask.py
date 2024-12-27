import subprocess
from astropy.io import fits
from pathlib import Path
import argparse
import numpy as np
from scipy import ndimage
from scipy.ndimage import binary_fill_holes, binary_dilation
import os

def source_extractor_call(data_path,det_minarea,det_thresh,outname,save_fits):
    subprocess.call(f"source-extractor {data_path} -c detect.sex -DETECT_MINAREA {det_minarea} -DETECT_THRESH {det_thresh} -CHECKIMAGE_NAME {Path.cwd()/outname}", shell=True, cwd=Path.cwd()/'sextractor')
    with fits.open(outname) as hdul:
        segmap = hdul[0].data
        segmap[np.isnan(segmap)] = 0
        segmap[segmap>0]=1
        segmap = segmap.astype(bool)
    if not save_fits:
        os.unlink(Path.cwd()/outname)
    return segmap

def create_dwarfplacement_mask(data_path,save_fits,verbose):
    detect_minarea, detect_thresh = 200, 1
    if verbose:
        print(f"running source-extractor with detect_minarea={detect_minarea} and detect_thresh={detect_thresh}...")
    segmap_sm = source_extractor_call(data_path,detect_minarea,detect_thresh,'segmap_sm.fits',save_fits)
    
    detect_minarea, detect_thresh = 20000, 1
    if verbose:
        print(f"running source-extractor with detect_minarea={detect_minarea} and detect_thresh={detect_thresh}...")
    segmap_lg = source_extractor_call(data_path,detect_minarea,detect_thresh,'segmap_lg.fits',save_fits)

    kernel = np.zeros((9,9))
    for i in range(9):
        for j in range(9):
            if ((i-4)**2+(j-4)**2) <= 16:
                kernel[i,j] = 1

    if verbose:
        print("dilating objects in small objects segmap...")
    segmap_sm_dilated = binary_dilation(segmap_sm,structure=kernel,iterations=3)

    if verbose:
        print("filling holes in small objects segmap...")
    segmap_sm_filled = binary_fill_holes(segmap_sm_dilated)

    if verbose:
        print("dilating objects in large objects segmap...")
    segmap_lg_dilated = binary_dilation(segmap_lg,structure=kernel,iterations=10)

    if verbose:
        print("filling holes in large objects segmap...")
    segmap_lg_filled = binary_fill_holes(segmap_lg_dilated)

    objects_mask = (segmap_sm_filled | segmap_lg_filled)

    with fits.open(data_path) as hdul:
        data = hdul[0].data

    if verbose:
        print("getting outer nan mask...")
    outernan_mask = ~binary_fill_holes(~np.isnan(data))

    if verbose:
        print("dilating outer nan mask...")
    dilated_outernan_mask = binary_dilation(outernan_mask,structure=ndimage.generate_binary_structure(2, 2),iterations=256)

    total_mask = (dilated_outernan_mask | objects_mask)

    if save_fits:
        fits.writeto('total_mask.fits',total_mask.astype(np.uint8),overwrite=True)
        fits.writeto('outer_mask.fits',dilated_outernan_mask.astype(np.uint8),overwrite=True)
        
    np.save('total_mask.npy',~(total_mask.astype(bool)))
    np.save('outer_mask.npy',~(dilated_outernan_mask.astype(bool)))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_path', help='Input image to create a mask from.')
    parser.add_argument('--save_fits', action='store_true', help='Saves fits files for the masks, allowing you to inspect them. Usually this is not done due to how much space they take up on disk.')
    parser.add_argument('--verbose', action='store_true', help='progress messages to terminal')

    args = parser.parse_args()
    data_path = Path(args.data_path).resolve()
    save_fits = args.save_fits
    verbose = args.verbose

    create_dwarfplacement_mask(data_path,save_fits,verbose)
