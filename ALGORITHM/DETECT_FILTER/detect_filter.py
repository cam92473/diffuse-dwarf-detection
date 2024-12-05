import subprocess
import time
import pandas as pd
import os
import numpy as np
from astropy.io import fits
import PIL.Image
import PIL.ImageFilter
import cv2
import sys
import threading
import shutil
from scipy.spatial.distance import squareform, pdist
from scipy.ndimage import binary_dilation
from itertools import accumulate
import operator
import warnings
import argparse
from datetime import datetime
from pathlib import Path

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
    rgba_image = PIL.Image.fromarray(rgba_arr,'RGBA')
    mask = rgba_image.filter(PIL.ImageFilter.MaxFilter)

    return mask

def fits_to_pil(processed_file):
    with fits.open(processed_file) as hdul:
        data = np.flip(hdul[0].data,axis=0)
    upbound = np.nanpercentile(data,99.9)
    lobound = np.nanpercentile(data,0.1)
    data[data>upbound] = upbound
    data[data<lobound] = lobound
    data[np.isnan(data)] = lobound
    data -= data.min()
    data *= 215./data.max()
    data += 30

    return PIL.Image.fromarray(np.uint8(data)).convert('RGB')

def make_composite_jpeg(name,prev_ids,new_ids,segmap,processed,blue,red,detectfilter_dir,signature):
    blue_ids = new_ids
    red_ids = np.setdiff1d(prev_ids,new_ids)
    blue_mask = get_mask_from_ids(blue_ids,segmap)
    red_mask = get_mask_from_ids(red_ids,segmap)
    first_composite = PIL.Image.composite(blue,processed,blue_mask)
    final_composite = PIL.Image.composite(red,first_composite,red_mask)
    final_composite.save(detectfilter_dir/f'{signature}_{name}.jpeg')

def initiate_gimp():
    gimp_command = (
    "pipe = open('Pipe', 'w');"
    "pipe.write('gimp opened successfully');"
    "pipe.close();"
    )
    subprocess.run(f"flatpak run org.gimp.GIMP//stable --batch-interpreter python-fu-eval -b \"{gimp_command}\"", shell=True, stdout=sys.stdout, stderr=open(os.devnull, 'w'))

def display_filter_image(detectfilter_dir,name,signature,i):
    gimp_command = (
    "(pdb.gimp_display_new(pdb.file_jpeg_load('%s', '%s')), pdb.gimp_displays_flush()) if (%d==0)"
    " else (pdb.gimp_image_insert_layer(gimp.image_list()[0], pdb.gimp_file_load_layer(gimp.image_list()[0],'%s'), None, -1), pdb.gimp_displays_flush())"
    ) % (detectfilter_dir/f'{signature}_{name}.jpeg', detectfilter_dir/f'{signature}_{name}.jpeg', i, detectfilter_dir/f'{signature}_{name}.jpeg')
    subprocess.run(f"flatpak run org.gimp.GIMP//stable --batch-interpreter python-fu-eval -b \"{gimp_command}\"", shell=True, stdout=sys.stdout, stderr=open(os.devnull, 'w'))

def quit_gimp():
    subprocess.run(f"flatpak run org.gimp.GIMP//stable --batch-interpreter python-fu-eval -b 'pdb.gimp_quit(1)'", shell=True, stdout=sys.stdout, stderr=open(os.devnull, 'w'))

def filter_by_sextractor_parameters(csv,processed_file):
    number = csv['NUMBER']
    filters = []
    descriptions = ['    raw detections']

    '''isoarea = csv['ISOAREA_IMAGE']
    large = sigma_clip(isoarea,sigma_upper=3,sigma_lower=np.inf).mask & (number>0)
    
    snrwin = csv['SNR_WIN']
    high_snr = sigma_clip(snrwin,sigma_upper=3,sigma_lower=np.inf).mask & (number > 0)

    not_halo_remnant_like = ~(large & high_snr & elliptical)

    filters.append(not_halo_remnant_like)
    descriptions.append('   elliptical_halo_remnant')'''

    '''fluxmax = csv['FLUX_MAX']
    high_fluxmax = sigma_clip(fluxmax,sigma_upper=2,sigma_lower=np.inf).mask & (number > 0)
    filters.append(high_fluxmax)
    descriptions.append('    fluxmax')'''

    '''fwhm = csv['FWHM_IMAGE']
    profile_not_too_flat = ~(sigma_clip(fwhm,sigma_upper=3,sigma_lower=np.inf).mask & (number > 0))
    filters.append(profile_not_too_flat)
    descriptions.append('   fwhm')'''

    '''x = csv['X_IMAGE']
    y = csv['Y_IMAGE']
    xpeak = csv['XPEAK_IMAGE']
    ypeak = csv['YPEAK_IMAGE']
    asymmetry = (x-xpeak)**2+(y-ypeak)**2
    not_asymmetric = ~(sigma_clip(asymmetry,sigma_lower=np.inf,sigma_upper=3).mask & (number > 0))
    filters.append(not_asymmetric)
    descriptions.append('   asymmetric')'''

    ''''''

    '''ellipticity = csv['ELLIPTICITY']
    not_elliptical = ~(ellipticity >= 0.5)
    filters.append(not_elliptical)
    descriptions.append('    ellipticity')

    flags = csv['FLAGS']
    not_flagged = ~((flags>0)&(flags!=4)&(flags!=16))
    filters.append(not_flagged)
    descriptions.append('    flagged')'''

    with fits.open(processed_file) as hdul:
        data = hdul[0].data
    nanmask = np.isnan(data)
    if nanmask.sum() > 0:
        nanmask = binary_dilation(nanmask,iterations=256)
    bordermask = np.zeros(data.shape,dtype=bool)
    bordermask[:256,:] = True
    bordermask[-256:,:] = True
    bordermask[:,:256] = True
    bordermask[:,-256:] = True
    edge_proximity_mask = (nanmask | bordermask)
    coords = csv[['X_IMAGE','Y_IMAGE']].astype(int)
    not_too_close_edge = ~(edge_proximity_mask[coords['Y_IMAGE'],coords['X_IMAGE']] & (number > 0))
    filters.append(not_too_close_edge)
    descriptions.append('    proximity_edge')

    '''warnings.simplefilter(action='ignore', category=FutureWarning)
    remaining_csv = csv[pd.concat(filters,axis=1).all(axis=1)]
    if remaining_csv.shape[0] > 1:
        distance_matrix = pd.DataFrame(squareform(pdist(remaining_csv[['X_IMAGE','Y_IMAGE']])),index=remaining_csv.index)
        updated_dm = distance_matrix.mask(distance_matrix==0, distance_matrix.max(axis=1), axis=0)
        tc_updater = (updated_dm<100).any(axis=1)
        too_close_mutual = (number<0).copy()
        too_close_mutual.update(tc_updater.astype(bool))
        not_too_close_mutual = ~(too_close_mutual.astype(bool))
        filters.append(not_too_close_mutual)
        descriptions.append('    proximity_mutual')'''

    return number, filters, descriptions

def filter_detections(csv,segmap,processed_file,csv_dir,segmap_dir,save_dir,save,play_through,signature,verbosity):
    if verbosity > 0:
        print("   filtering detections...")

    letters = iter(list('EFGHIJKLMNOPQRSTUVWXYZ'))
    number, filters, descriptions = filter_by_sextractor_parameters(csv,processed_file)

    filtered_csv = csv[pd.concat(filters,axis=1).all(axis=1)]
    descriptions.append('    filtered detections')
    filtered_csv.to_csv(csv_dir/f'{signature}_filtered_detections.csv',index=False)
    mask = np.isin(segmap,filtered_csv['NUMBER'])
    filtered_detections = segmap.copy()
    filtered_detections[~mask] = 0
    fits.writeto(segmap_dir/f'{signature}_filtered_detections.fits',filtered_detections,overwrite=True)

    '''if save:
    shutil.copyfile(paths["csv"]/f'{signature}_raw_detections.csv',paths["save"]/f'{signature}_raw_detections.csv')
    shutil.copyfile(paths["csv"]/f'{signature}_filtered_detections.csv',paths["save"]/f'{signature}_filtered_detections.csv')
    shutil.copyfile(paths["images"]/f'{signature}_raw_detections.fits',paths["save"]/f'{signature}_raw_detections.fits')
    shutil.copyfile(paths["images"]/f'{signature}_filtered_detections.fits',paths["save"]/f'{signature}_filtered_detections.fits')'''

    if (save | play_through):
        openlayer_print_delay = 2
        filtered_time = 5
        anded_filters_list = list(accumulate(filters,operator.and_))
        ids_list = [number, number]
        ids_list = ids_list + [number[anded_filters_list[i]] for i in range(len(filters))]
        ids_list.append(number[anded_filters_list[-1]])
        num_removed  = [len(ids_list[i])-len(ids_list[i+1]) for i in range(len(ids_list)-1)]
        names = [next(letters)+'_'+descriptions[i][4:] for i in range(len(descriptions))]
        messages = [descriptions[i]+": "+str(num_removed[i])+" detections removed" if (i!=0)&(i!=(len(descriptions)-1)) else descriptions[i]+" ("+str(len(ids_list[i+1]))+")" for i in range(len(descriptions))]
        processed = fits_to_pil(processed_file)
        blue = PIL.Image.new('RGB', processed.size, 'blue')
        red = PIL.Image.new('RGB', processed.size, 'red')
        if play_through:
            os.mkfifo('Pipe')
            t1 = threading.Thread(target=initiate_gimp)
            t1.start()
            checking_if_gimp_open = True
            with open('Pipe','r') as pipe:
                while checking_if_gimp_open:
                    line = pipe.readline().strip()
                    if line=='gimp opened successfully':
                        checking_if_gimp_open=False
            os.remove('Pipe')
        for i in range(len(ids_list)-1):
            prev_ids = ids_list[i]
            new_ids = ids_list[i+1]
            name = names[i]
            make_composite_jpeg(name,prev_ids,new_ids,segmap,processed,blue,red,segmap_dir,signature)
            if play_through:
                display_filter_image(segmap_dir,name,signature,i)
                time.sleep(openlayer_print_delay)
            if verbosity > 0:
                print(messages[i])
            if play_through:
                if i==(len(ids_list)-2):
                    time.sleep(filtered_time)
        if play_through:
            quit_gimp()
            t1.join()
        if save:
            for name in names:
                shutil.copyfile(segmap_dir/f'{signature}_{name}.jpeg',save_dir/f'{signature}_{name}.jpeg')

def get_csv(csv_dir,signature):
    cat = pd.read_table(csv_dir/f'{signature}_raw_detections.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','ALPHA_J2000','DELTA_J2000','X_IMAGE','Y_IMAGE','FLUX_RADIUS','MAG_AUTO','MAGERR_AUTO','FLUX_ISO','FLUXERR_ISO','MAG_ISO','MAGERR_ISO','FLUX_ISOCOR','FLUXERR_ISOCOR','MAG_ISOCOR','MAGERR_ISOCOR','FLUX_WIN','MAG_WIN','SNR_WIN','FLUX_GROWTH','FLUX_GROWTHSTEP','ELLIPTICITY','CLASS_STAR','BACKGROUND','FLUX_MAX','ISOAREA_IMAGE','XPEAK_IMAGE','YPEAK_IMAGE','XMIN_IMAGE','YMIN_IMAGE','XMAX_IMAGE','YMAX_IMAGE','XPEAK_FOCAL','YPEAK_FOCAL','X_FOCAL','Y_FOCAL','X2_IMAGE','Y2_IMAGE','CXX_IMAGE','CYY_IMAGE','CXY_IMAGE','CXXWIN_IMAGE','CYYWIN_IMAGE','CXYWIN_IMAGE','FLAGS','FLAGS_WIN','ISO0','ISO1','ISO2','ISO3','ISO4','ISO5','ISO6','ISO7','FWHM_IMAGE']
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
    parser.add_argument('--play_through', action='store_true', default=False, help='Toggles play-through mode, where you observe the algorithm filtering out the detections in the GIMP interface.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=['0','1','2'], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()

    detect_filter(Path(args.processed_file).resolve(),Path(args.segmap_dir).resolve(),Path(args.csv_dir).resolve(),Path(args.sextractor_dir).resolve(),Path(args.save_dir).resolve(),args.detect_params,args.name,args.save,args.play_through,args.signature,int(args.verbosity))
