import argparse
from pathlib import Path
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
import time
from astropy.wcs import WCS
import PIL.Image
import PIL.ImageFilter
import pandas as pd
from natsort import natsorted
import glob
import cv2
import shutil

def get_bounds(arr):
    hist = np.histogram(arr[~np.isnan(arr)],bins=10000)
    left_ind = np.argmax(hist[0])
    mode = hist[1][left_ind]
    vmin = mode
    vmax = np.nanpercentile(arr,98)
    return vmin, vmax   

def log_normalize_with_vbounds(arr,vmin,vmax):
    arr[arr<vmin] = vmin
    arr[arr>vmax] = vmax
    return np.log10(arr)

def save_to_jpg(arr,normalize,saveloc,cmap):
    if normalize == 'log_norm':
        arr = arr-np.nanmin(arr)+1
        arr[np.isnan(arr)] = 1
        vmin, vmax = get_bounds(arr)
        logarr = log_normalize_with_vbounds(arr,vmin,vmax)
        plt.imsave(saveloc,logarr,cmap=cmap,origin='lower')
    elif normalize == "boundary_norm":
        arr[arr>1] = 1
        plt.imsave(saveloc,arr,cmap=cmap,origin='lower')
    elif normalize == 'none':
        plt.imsave(saveloc,arr,cmap=cmap,origin='lower')

def get_rgb_cutout(output_root,phot_filters,rgb_dir,signature,filter_dir):
    with fits.open(output_root/phot_filters[0]/f'{signature}_1a_data_{phot_filters[0]}.fits') as hdul:
        data = hdul[0].data
        data_header = hdul[0].header
    data_dims = data.shape
    data_wcs = WCS(data_header)
    with fits.open(rgb_dir/'tile4cut_i.fits') as hdul:
        rgb_header = hdul[0].header
    rgb_wcs = WCS(rgb_header)
    PIL.Image.MAX_IMAGE_PIXELS = np.inf
    rgb_image = PIL.Image.open(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1.jpg')
    rgb_dims = rgb_image.size
    x_semi = data_dims[1]/2
    y_semi = data_dims[0]/2
    skyc = data_wcs.pixel_to_world(x_semi,y_semi)
    rgbpix = rgb_wcs.world_to_pixel(skyc)
    cutout_dims = (rgbpix[0]-x_semi,rgb_dims[1]-rgbpix[1]-y_semi,rgbpix[0]+x_semi,rgb_dims[1]-rgbpix[1]+y_semi)
    data_rgb = rgb_image.crop(cutout_dims)
    data_rgb.save(filter_dir/f'{signature}_rgb_data.jpg')
    
    return data_rgb

def get_mask_from_ids(ids,rawdets_data,masktype):
    array_mask = np.isin(rawdets_data,ids)
    array = np.zeros(rawdets_data.shape,dtype=np.uint8)
    array[array_mask] = rawdets_data[array_mask]
    array = np.flip(array,axis=0)
    if masktype=='edge':
        array = cv2.Canny(array,0,1)
    alpha_array = np.copy(array)
    alpha_array[alpha_array>0] = 255
    rgba_array = np.dstack((array,array,array,alpha_array))
    rgba_image = PIL.Image.fromarray(rgba_array,'RGBA')
    mask = rgba_image.filter(PIL.ImageFilter.MaxFilter)

    return mask

def make_solid_composites(csv,remaining_ids,rawdets_data,colour,rgb_image,signature,filter_dir):
    table = pd.read_csv(csv)
    ids = table['NUMBER'].to_numpy()
    intersect_ids = np.intersect1d(remaining_ids,ids)
    solids = get_mask_from_ids(intersect_ids,rawdets_data,masktype='solid')
    colour_img = PIL.Image.new('RGB', rgb_image.size, colour)
    rgb_composite = PIL.Image.composite(colour_img,rgb_image,solids)
    name = csv.split(signature+'_')[1].split('.')[0]
    rgb_composite.save(filter_dir/'cumulative'/f'{signature}_{name}.jpg')
    remaining_ids = remaining_ids[~np.isin(remaining_ids,intersect_ids)]

    return rgb_composite, remaining_ids

def make_edge_composites(csv,rawdets_data,colour,rgb_image,blurred_image,masked_image,signature,filter_dir,save_to_cumulative=False):
    table = pd.read_csv(csv)
    ids = table['NUMBER'].to_numpy()
    edges = get_mask_from_ids(ids,rawdets_data,'edge')
    colour_img = PIL.Image.new('RGB', rgb_image.size, colour)
    rgb_composite = PIL.Image.composite(colour_img,rgb_image,edges)
    blurred_composite = PIL.Image.composite(colour_img,blurred_image,edges)
    masked_composite = PIL.Image.composite(colour_img,masked_image,edges)
    name = csv.split(signature+'_')[1].split('.')[0]
    rgb_composite.save(filter_dir/'individual'/f'{signature}_{name}.jpg')
    blurred_composite.save(filter_dir/'individual'/f'{signature}_{name}_blurred.jpg')
    masked_composite.save(filter_dir/'individual'/f'{signature}_{name}_masked.jpg')
    if save_to_cumulative:
        rgb_composite.save(filter_dir/'cumulative'/f'{signature}_{name}.jpg')

    return rgb_composite, blurred_composite, masked_composite

def populate_filter_dir(output_root,phot_filters,rgb_dir,signature,filter_dir):
    data_rgb = get_rgb_cutout(output_root,phot_filters,rgb_dir,signature,filter_dir)
    with fits.open(output_root/phot_filters[0]/f'{signature}_4_blurred_{phot_filters[0]}.fits') as hdul:
        saveloc = filter_dir/f'{signature}_blurred.jpg'    
        save_to_jpg(hdul[0].data,'log_norm',saveloc,'binary_r')
    data_blurred = PIL.Image.open(filter_dir/f'{signature}_blurred.jpg')
    with fits.open(output_root/phot_filters[0]/f'{signature}_3_data_masked_{phot_filters[0]}.fits') as hdul:
        saveloc = filter_dir/f'{signature}_masked.jpg'    
        save_to_jpg(hdul[0].data,'log_norm',saveloc,'binary_r')
    data_masked = PIL.Image.open(filter_dir/f'{signature}_masked.jpg')
    with fits.open(output_root/f'{signature}_6_raw_detections.fits') as hdul:
        rawdets_data = hdul[0].data
        saveloc = filter_dir/f'{signature}_raw_detections.jpg'
        save_to_jpg(rawdets_data.copy(),'boundary_norm',saveloc,'binary_r')

    csv_fold = filter_dir/'csv'
    shutil.copytree(output_root/'csv',csv_fold)
    csv_list = natsorted(glob.glob(str(csv_fold/'*.csv'))) 
                                    
    colours = ["red","green","blue","orange","purple","yellow","turquoise","violet","sienna","gray","dodgerblue","deeppink","greenyellow","darkblue","rebeccapurple","olive","teal","tomato","magenta","pink","lime","cornflowerblue","mediumspringgreen","maroon","indianred","gold","darkorange","limegreen"]

    raw_detections_csv = csv_list[0]
    raw_rgb_composite, raw_blurred_composite, raw_masked_composite = make_edge_composites(raw_detections_csv,rawdets_data,'lightsalmon',data_rgb,data_blurred,data_masked,signature,filter_dir,save_to_cumulative=True)
    raw_table = pd.read_csv(raw_detections_csv)
    remaining_ids = raw_table['NUMBER'].to_numpy()
    rgb_composite = raw_rgb_composite.copy()

    for i in range(1,len(csv_list)-1):
        csv = csv_list[i]
        make_edge_composites(csv,rawdets_data,colours[i-1],raw_rgb_composite,raw_blurred_composite,raw_masked_composite,signature,filter_dir,save_to_cumulative=False)
        rgb_composite, remaining_ids = make_solid_composites(csv,remaining_ids,rawdets_data,colours[i-1],rgb_composite,signature,filter_dir)
    
    filtered_detections_csv = csv_list[-1]
    make_edge_composites(filtered_detections_csv,rawdets_data,'white',data_rgb,data_blurred,data_masked,signature,filter_dir,save_to_cumulative=True)

def populate_stackdetect_dir(output_root,phot_filters,signature,stackdetect_dir):
    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        blurred = filt_dir/f'{signature}_4_blurred_{photfilt}.fits'
        with fits.open(blurred) as hdul:
            saveloc = stackdetect_dir/f'{signature}_4_blurred_{photfilt}.jpg'
            save_to_jpg(hdul[0].data,'log_norm',saveloc,'cividis')
    with fits.open(output_root/f'{signature}_5_stacked.fits') as hdul:
        saveloc = stackdetect_dir/f'{signature}_5_stacked.jpg'
        save_to_jpg(hdul[0].data,'log_norm',saveloc,'cividis')
    with fits.open(output_root/f'{signature}_6_raw_detections.fits') as hdul:
        saveloc = stackdetect_dir/f'{signature}_6_raw_detections.jpg'
        save_to_jpg(hdul[0].data,'boundary_norm',saveloc,'cividis')      

def populate_maskblur_dir(output_root,phot_filters,signature,maskblur_dir):
    for photfilt in phot_filters:
        maskblur_filt_dir = maskblur_dir/photfilt
        maskblur_filt_dir.mkdir()
        filt_dir = output_root/photfilt
        fits_images = natsorted(glob.glob(str(filt_dir/'*.fits')))
        tags = ['1a_data','1b_weight','1c_background','2a_segment_surf','2b_segment_deep','2c_brightobj_mask','2d_brightobj_masked','2e_segment_star','2f_star_mask','2g_segmap_deep_masked','3_data_masked','4_blurred']
        norms = ['log_norm','none','none','boundary_norm','boundary_norm','boundary_norm','log_norm','boundary_norm','boundary_norm','boundary_norm','log_norm','log_norm']
        #colours = ['cividis','cividis','cividis','gist_ncar','gist_ncar','cividis','cividis','gist_ncar','cividis','cividis','cividis','cividis']
        for i in range(len(tags)):
            with fits.open(fits_images[i]) as hdul:
                saveloc = maskblur_filt_dir/f'{signature}_{tags[i]}_{photfilt}.jpg'
                save_to_jpg(hdul[0].data,norms[i],saveloc,'cividis')
               
def setup_dirs(output_root):
    maskblur_dir = output_root/'records'/'mask_and_blur'
    maskblur_dir.mkdir(parents=True,exist_ok=True)
    stackdetect_dir = output_root/'records'/'stack_and_detect'
    stackdetect_dir.mkdir(parents=True,exist_ok=True)
    filter_dir = output_root/'records'/'filter'
    (filter_dir/'individual').mkdir(parents=True,exist_ok=True)
    (filter_dir/'cumulative').mkdir(parents=True,exist_ok=True)
    
    return maskblur_dir, stackdetect_dir, filter_dir


def save_records_func(output_root,phot_filters,rgb_dir,signature,verbose):

    t1 = time.perf_counter()

    maskblur_dir, stackdetect_dir, filter_dir = setup_dirs(output_root)

    populate_maskblur_dir(output_root,phot_filters,signature,maskblur_dir)
    populate_stackdetect_dir(output_root,phot_filters,signature,stackdetect_dir)
    populate_filter_dir(output_root,phot_filters,rgb_dir,signature,filter_dir)

    t2 = time.perf_counter()
    if verbose:
        print(f"saving records: {t2-t1}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('output_root', help='Path to the image input into the detection algorithm.')
    parser.add_argument('phot_filters', help='Path to the image input into the detection algorithm.')
    parser.add_argument('signature', help='Specify a new file name if you want to save the replotted image.')
    parser.add_argument('-saveim_folder', help='Specify a new file name if you want to save the replotted image.')
    

    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    phot_filters = list(args.phot_filters)
    if args.saveim_folder is not None:
        saveim_folder = Path(args.saveim_folder).resolve()
    else:
        saveim_folder = None
    signature = args.signature

    display_algorithm_steps(output_root,phot_filters,signature,saveim_folder)