import subprocess
import time
import pandas as pd
import os
import numpy as np
from astropy.io import fits
import sys
import argparse
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageFilter, ImageTk
import cv2
from astropy.stats import sigma_clip
import tkinter as tk
import warnings

def get_mask_from_ids(ids,segmap):
    arr_mask = np.isin(segmap,ids)
    arr = np.zeros(segmap.shape,dtype=np.uint8)
    arr[arr_mask] = segmap[arr_mask]
    flipped_arr = np.flip(arr,axis=0)
    edges_arr = cv2.Canny(flipped_arr,0,1)
    dilate_kernel = np.ones((3, 3), np.uint8)
    thicker_edges_arr = cv2.dilate(edges_arr, dilate_kernel, iterations=2)
    alpha_arr = np.copy(thicker_edges_arr)
    alpha_arr[alpha_arr>0] = 255
    rgba_arr = np.dstack((edges_arr,edges_arr,edges_arr,alpha_arr))
    rgba_image = Image.fromarray(rgba_arr,'RGBA')
    mask = rgba_image.filter(ImageFilter.MaxFilter)

    return mask

def make_composite_jpeg(image,segmap,blue,red,blue_ids,red_ids):
    blue_mask = get_mask_from_ids(blue_ids,segmap)
    red_mask = get_mask_from_ids(red_ids,segmap)
    first_composite = Image.composite(blue,image,blue_mask)

    return Image.composite(red,first_composite,red_mask)

def fits_to_pil(data):
    warnings.filterwarnings("ignore", category=UserWarning, module="astropy.stats.sigma_clipping")
    data_copy = np.copy(data)
    clipped = sigma_clip(data_copy,sigma=3)
    median = np.nanmedian(data_copy)
    hi_mask = clipped.mask & (data_copy>median)
    lo_mask = clipped.mask & (data_copy<median)
    data_copy[hi_mask] = np.nanmax(data_copy[~clipped.mask])
    data_copy[lo_mask] = np.nanmin(data_copy[~clipped.mask])
    data_copy -= np.nanmin(data_copy)
    data_copy *= 255/np.nanmax(data_copy)
    data_copy = np.flipud(data_copy)
    image = Image.fromarray(data_copy)
    image = image.convert('RGB')

    return image

def tk_display(final_composite,title):
    root = tk.Tk()
    root.title(title)
    final_composite.thumbnail((800, 800))
    photo = ImageTk.PhotoImage(final_composite)
    width, height = final_composite.size
    root.geometry(f"{width}x{height}")
    label = tk.Label(root, image=photo)
    label.pack()
    root.after(3000, root.destroy)
    root.mainloop()

def filter_detections(csv,segmap,processed_file,csv_dir,segmap_dir,save_dir,save,play_through,signature,verbosity):
    if verbosity > 0:
        print("   removing edge detections...")

    with fits.open(processed_file) as hdul:
        data = hdul[0].data
    bordermask = np.zeros(data.shape,dtype=bool)
    bordermask[:100,:] = True
    bordermask[-100:,:] = True
    bordermask[:,:100] = True
    bordermask[:,-100:] = True
    coords = csv[['Y_IMAGE','X_IMAGE']].values.astype(int)
    safe = ~bordermask[coords.T[0],coords.T[1]]

    filtered_csv = csv[safe]
    filtered_csv.to_csv(csv_dir/f'{signature}_filtered_detections.csv',index=False)
    blue_ids = filtered_csv['NUMBER']
    red_ids = csv[~safe]['NUMBER']
    mask = np.isin(segmap,blue_ids)
    filtered_detections = segmap.copy()
    filtered_detections[~mask] = 0
    fits.writeto(segmap_dir/f'{signature}_filtered_detections.fits',filtered_detections,overwrite=True)

    if (save | play_through):
        image = fits_to_pil(data)
        blue = Image.new('RGB', image.size, 'blue')
        red = Image.new('RGB', image.size, 'red')
        final_composite = make_composite_jpeg(image,segmap,blue,red,blue_ids,red_ids)
        if save:
            final_composite.save(save_dir/f'{signature}_edge_detections_removed.jpeg')
        if play_through:
            tk_display(final_composite,'Edge detections removed')

def get_csv(csv_dir,signature):
    cat = pd.read_table(csv_dir/f'{signature}_raw_detections.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','ALPHA_J2000','DELTA_J2000','X_IMAGE','Y_IMAGE']
    cat.to_csv(csv_dir/f'{signature}_raw_detections.csv',index=False,header=header)
    os.remove(csv_dir/f'{signature}_raw_detections.catalog')
    csv = pd.read_csv(csv_dir/f'{signature}_raw_detections.csv')

    return csv

def source_extractor_call(processed_file,segmap_dir,csv_dir,sextractor_dir,detect_params,signature,verbosity):
    detect_minarea = detect_params[0]
    detect_thresh = detect_params[1]
    if verbosity == 0:
        stdout = open(os.devnull, 'w')
        stderr = open(os.devnull, 'w')
    elif verbosity > 0:
        stdout = sys.stdout
        stderr = sys.stderr
    if verbosity > 0:
        print("   calling source-extractor...")
    subprocess.run(f"source-extractor {processed_file} -c detect.sex -DETECT_MINAREA {detect_minarea} -DETECT_THRESH {detect_thresh} -ANALYSIS_THRESH {detect_thresh} -CHECKIMAGE_NAME {segmap_dir/f'{signature}_raw_detections.fits'} -CATALOG_NAME {csv_dir/f'{signature}_raw_detections.catalog'}", shell=True, cwd=sextractor_dir, stdout=stdout, stderr=stderr)
    with fits.open(segmap_dir/f'{signature}_raw_detections.fits') as hdul:
        segmap = hdul[0].data

    return segmap

def create_signature(processed_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{processed_file.stem}_{timestr}"
    return signature

def detect_filter(processed_file, segmap_dir, csv_dir, sextractor_dir, save_dir, detect_params, name="", save=False, play_through=False, signature=None, verbosity=1):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(f"  Detecting and filtering{name}...")

    create_signature(processed_file,signature)
    segmap = source_extractor_call(processed_file,segmap_dir,csv_dir,sextractor_dir,detect_params,signature,verbosity)
    csv = get_csv(csv_dir,signature)
    filter_detections(csv,segmap,processed_file,csv_dir,segmap_dir,save_dir,save,play_through,signature,verbosity)

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"  Finished detecting and filtering{name}. Total time: {t2-t1}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('processed_file', help='Image processed file that you want to detect and filter diffuse objects from.')
    parser.add_argument('segmap_dir', help='Directory where segmentation maps will be saved.')
    parser.add_argument('csv_dir', help='Directory where csvs containing the detection coordinates and parameters will be saved.')
    parser.add_argument('sextractor_dir', help='Directory with source-extractor utilities.')
    parser.add_argument('-save_dir', help='If --save is toggled, images showing the filtering steps will be saved here.')
    parser.add_argument('-detect_params', nargs=2, type=int, default=[500,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the median-filtered image.')
    parser.add_argument('--name', default="", help='Optional argument affecting only the content of the print statements.')
    parser.add_argument('--save', action='store_true', default=False, help='Whether to save images showing the filtering steps.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=['0','1','2'], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()

    detect_filter(Path(args.processed_file).resolve(),Path(args.segmap_dir).resolve(),Path(args.csv_dir).resolve(),Path(args.sextractor_dir).resolve(),Path(args.save_dir).resolve(),args.detect_params,args.name,args.save,args.play_through,args.signature,int(args.verbosity))
