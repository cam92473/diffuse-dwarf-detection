import subprocess
import time
import pandas as pd
import os
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clip
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

def get_mask_from_ids(ids,segmap):
    arr_mask = np.isin(segmap,ids)
    arr = np.zeros(segmap.shape,dtype=np.uint8)
    arr[arr_mask] = segmap[arr_mask]
    flipped_arr = np.flip(arr,axis=0)
    edges_arr = cv2.Canny(flipped_arr,0,1)
    alpha_arr = np.copy(edges_arr)
    alpha_arr[alpha_arr>0] = 255
    rgba_arr = np.dstack((edges_arr,edges_arr,edges_arr,alpha_arr))
    rgba_image = PIL.Image.fromarray(rgba_arr,'RGBA')
    mask = rgba_image.filter(PIL.ImageFilter.MaxFilter)

    return mask

def fits_to_pil(blurred_path):
    with fits.open(blurred_path) as hdul:
        data = np.flip(hdul[0].data,axis=0)
    upbound = np.nanpercentile(data,99)
    lobound = np.nanpercentile(data,1)
    data[data>upbound] = upbound
    data[data<lobound] = lobound
    data[np.isnan(data)] = lobound
    data -= data.min()
    data *= 255./data.max()

    return PIL.Image.fromarray(np.uint8(data)).convert('RGB')

def make_composite_jpeg(name,prev_ids,new_ids,segmap,blurred,blue,red,detectfilter_dir,signature):
    blue_ids = new_ids
    red_ids = np.setdiff1d(prev_ids,new_ids)
    blue_mask = get_mask_from_ids(blue_ids,segmap)
    red_mask = get_mask_from_ids(red_ids,segmap)
    first_composite = PIL.Image.composite(blue,blurred,blue_mask)
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

def filter_detections(paths,csv,segmap,save,play_through,signature,verbosity):
    if verbosity > 0:
        print(" filtering detections...")

    filters = []
    descriptions = ['   raw detections']

    number = csv['NUMBER']

    '''isoarea = csv['ISOAREA_IMAGE']
    large = sigma_clip(isoarea,sigma_upper=2,sigma_lower=np.inf).mask & (number>0)
    filters.append(large)
    descriptions.append('   isoarea')'''

    '''fluxmax = csv['FLUX_MAX']
    high_fluxmax = sigma_clip(fluxmax,sigma_upper=2,sigma_lower=np.inf).mask & (number > 0)
    filters.append(high_fluxmax)
    descriptions.append('    fluxmax')'''

    '''snrwin = csv['SNR_WIN']
    high_snr = sigma_clip(snrwin,sigma_upper=1.5,sigma_lower=np.inf).mask & (number > 0)
    filters.append(high_snr)
    descriptions.append('   snrwin')'''

    '''ellipticity = csv['ELLIPTICITY']
    circular = (ellipticity <= 0.3)
    filters.append(circular)
    descriptions.append('   ellipticity')'''

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

    flags = csv['FLAGS']
    not_flagged = ~((flags==2) | (flags==3) | (flags==18) | (flags==19))
    filters.append(not_flagged)
    descriptions.append('   flagged')

    with fits.open(paths['blurred_file']) as hdul:
        data = hdul[0].data
    nanmask = np.isnan(data)
    if nanmask.sum() > 0:
        nanmask = binary_dilation(nanmask,iterations=128)
    bordermask = np.zeros(data.shape,dtype=bool)
    bordermask[:128,:] = True
    bordermask[-128:,:] = True
    bordermask[:,:128] = True
    bordermask[:,-128:] = True
    edge_proximity_mask = (nanmask | bordermask)
    coords = csv[['X_IMAGE','Y_IMAGE']].astype(int)
    not_too_close_edge = ~(edge_proximity_mask[coords['Y_IMAGE'],coords['X_IMAGE']] & (number > 0))
    filters.append(not_too_close_edge)
    descriptions.append('   proximity_edge')

    remaining_csv = csv[pd.concat(filters,axis=1).all(axis=1)]
    if remaining_csv.shape[0] > 1:
        distance_matrix = pd.DataFrame(squareform(pdist(remaining_csv[['X_IMAGE','Y_IMAGE']])),index=remaining_csv.index)
        updated_dm = distance_matrix.mask(distance_matrix==0, distance_matrix.max(axis=1), axis=0)
        tc_updater = (updated_dm<100).any(axis=1)
        too_close_mutual = (number<0).copy()
        too_close_mutual.update(tc_updater)
        not_too_close_mutual = ~(too_close_mutual.astype(bool))
        filters.append(not_too_close_mutual)
        descriptions.append('   proximity_mutual')

    filtered_csv = csv[pd.concat(filters,axis=1).all(axis=1)]
    descriptions.append('   filtered detections')
    filtered_csv.to_csv(paths["csv"]/f'{signature}_filtered_detections.csv',index=False)
    mask = np.isin(segmap,filtered_csv['NUMBER'])
    filtered_detections = segmap.copy()
    filtered_detections[~mask] = 0
    fits.writeto(paths["images"]/f'{signature}_filtered_detections.fits',filtered_detections,overwrite=True)

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
        letters = 'DEFGHIJKLMNOP'
        names = [letters[i]+'_'+descriptions[i][3:] for i in range(len(descriptions))]
        messages = [descriptions[i]+": "+str(num_removed[i])+" detections removed" if (i!=0)&(i!=(len(descriptions)-1)) else descriptions[i]+" ("+str(len(ids_list[i+1]))+")" for i in range(len(descriptions))]
        blurred = fits_to_pil(paths['blurred_file'])
        blue = PIL.Image.new('RGB', blurred.size, 'blue')
        red = PIL.Image.new('RGB', blurred.size, 'red')
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
            make_composite_jpeg(name,prev_ids,new_ids,segmap,blurred,blue,red,paths["images"],signature)
            if play_through:
                display_filter_image(paths["images"],name,signature,i)
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
                shutil.copyfile(paths["images"]/f'{signature}_{name}.jpeg',paths["save"]/f'{signature}_{name}.jpeg')

    return filtered_csv

def source_extractor_call(blurred_file,paths,detect_params,signature,verbosity):
    detect_minarea = detect_params[0]
    detect_thresh = detect_params[1]
    if verbosity > 0:
        print(" getting objects with source-extractor...")
    subprocess.call(f"source-extractor {blurred_file} -c detect.sex -DETECT_MINAREA {detect_minarea} -DETECT_THRESH {detect_thresh} -ANALYSIS_THRESH {detect_thresh} -CHECKIMAGE_NAME {paths['images']/f'{signature}_raw_detections.fits'} -CATALOG_NAME {paths['csv']/f'{signature}_raw_detections.catalog'}", shell=True, cwd=paths["sextractor"])
    with fits.open(paths["images"]/f'{signature}_raw_detections.fits') as hdul:
        segmap = hdul[0].data

    return segmap

def get_csv(paths,signature):
    cat = pd.read_table(paths["csv"]/f'{signature}_raw_detections.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','ALPHA_J2000','DELTA_J2000','X_IMAGE','Y_IMAGE','FLUX_RADIUS','MAG_AUTO','MAGERR_AUTO','FLUX_ISO','FLUXERR_ISO','MAG_ISO','MAGERR_ISO','FLUX_ISOCOR','FLUXERR_ISOCOR','MAG_ISOCOR','MAGERR_ISOCOR','FLUX_WIN','MAG_WIN','SNR_WIN','FLUX_GROWTH','FLUX_GROWTHSTEP','ELLIPTICITY','CLASS_STAR','BACKGROUND','FLUX_MAX','ISOAREA_IMAGE','XPEAK_IMAGE','YPEAK_IMAGE','XMIN_IMAGE','YMIN_IMAGE','XMAX_IMAGE','YMAX_IMAGE','XPEAK_FOCAL','YPEAK_FOCAL','X_FOCAL','Y_FOCAL','X2_IMAGE','Y2_IMAGE','CXX_IMAGE','CYY_IMAGE','CXY_IMAGE','CXXWIN_IMAGE','CYYWIN_IMAGE','CXYWIN_IMAGE','FLAGS','FLAGS_WIN','ISO0','ISO1','ISO2','ISO3','ISO4','ISO5','ISO6','ISO7','FWHM_IMAGE']
    cat.to_csv(paths["csv"]/f'{signature}_raw_detections.csv',index=False,header=header)
    os.remove(paths["csv"]/f'{signature}_raw_detections.catalog')
    csv = pd.read_csv(paths["csv"]/f'{signature}_raw_detections.csv')
    
    return csv

def clip_and_convert(cutout):
    clipped = sigma_clip(cutout,sigma=5)
    below = (cutout<np.median(cutout))&clipped.mask
    above = (cutout>np.median(cutout))&clipped.mask
    cutout[below] = cutout[~below].min()
    cutout[above] = cutout[~above].max()
    cutout -= cutout.min()
    cutout *= 65534/cutout.max()
    return cutout

def cutout_filtered_detections(paths,filtered_csv,verbosity):

    if verbosity > 0:
        print(" making cutouts...")
    with fits.open(paths['clipped_file']) as hdul:
        data = hdul[0].data
    x, y = filtered_csv['X_IMAGE'].to_numpy(), filtered_csv['Y_IMAGE'].to_numpy()
    r, c = (y-1).astype(int), (x-1).astype(int)
    data_pad = np.pad(data,128,mode='constant',constant_values=np.nanmin(data))
    for i in range(len(filtered_csv)):
        cutout = data_pad[r[i]:r[i]+256,c[i]:c[i]+256].copy()
        cutout = clip_and_convert(np.flipud(cutout))
        im = PIL.Image.fromarray(np.uint16(cutout),'I;16')
        im.save(paths["cutouts"]/f'co_{i}_{r[i]}_{c[i]}.png')

def detect_filter_cutout(blurred_file, paths, detect_params, save, play_through, signature, verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print("DETECT, FILTER & CUTOUT")

    segmap = source_extractor_call(blurred_file,paths,detect_params,signature,verbosity)
    csv = get_csv(paths,signature)
    filtered_csv = filter_detections(paths,csv,segmap,save,play_through,signature,verbosity)
    cutout_filtered_detections(paths,filtered_csv,verbosity)

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"DETECT, FILTER & CUTOUT time: {t2-t1}")