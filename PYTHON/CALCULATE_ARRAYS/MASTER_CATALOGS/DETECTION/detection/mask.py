import numpy as np
from astropy.io import fits
import argparse
import time
import subprocess
import pandas as pd
import os
from astropy.stats import sigma_clip
from scipy.ndimage import binary_dilation
import numpy as np

def get_circular_kernel(rad):
    kernel = np.zeros((2*rad+1)**2).reshape(2*rad+1,2*rad+1)
    for i in range(2*rad+1):
        for j in range(2*rad+1):
            if (rad-i)**2 + (rad-j)**2 <= rad**2:
                kernel[i,j] = 1
    
    return kernel

def dilate_mask(mask,rad):
    kernel = get_circular_kernel(rad)
    dilated = binary_dilation(mask,kernel)

    return dilated

def get_hot_pixels_mask(filt_dir,photfilt,signature,dilated_mask):
    data_path = filt_dir/f'{signature}_1a_data_{photfilt}.fits'
    with fits.open(data_path) as hdul:
        data = hdul[0].data
    temp_data = data.copy()
    temp_data[dilated_mask] = 0
    hot_pixels_mask = sigma_clip(temp_data,sigma=10,masked=True).mask

    return hot_pixels_mask

def apply_masks(filt_dir,photfilt,signature,dilated_mask,hot_pixels_mask,background):
    data_path = filt_dir/f'{signature}_1a_data_{photfilt}.fits'
    with fits.open(data_path) as hdul:
        data = hdul[0].data
    combined_mask = dilated_mask | hot_pixels_mask
    noise = np.random.normal(0,0.5*np.nanstd(data[~combined_mask]),size=data.shape)
    data[combined_mask] = background[combined_mask] + noise[combined_mask]

    return data, combined_mask

def filter_segmap(segmap,csv,filt_dir,photfilt,signature):

    flags = csv['FLAGS']
    flagswin = csv['FLAGS_WIN']
    #flagged = (flags >= 16) | (flagswin >= 8)
    aperture_data_incomplete = (flags>=16)
    flagswin_zero = (flagswin == 0)
    flagswin_eight = (flagswin == 8)

    isoarea = csv['ISOAREA_IMAGE']
    above_analysis_thresh = isoarea>50
    
    reduced_csv = csv[~above_analysis_thresh]
    number = reduced_csv['NUMBER']

    background = reduced_csv['BACKGROUND']
    high_background = (sigma_clip(background,sigma=5).mask) & (number > 0) #the latter condition serves to coerce it into a series

    fluxmax = reduced_csv['FLUX_MAX']
    high_fluxmax = (sigma_clip(fluxmax).mask) & (number > 0)

    halflight_radius = reduced_csv['FLUX_RADIUS_50']
    isoareaf = reduced_csv['ISOAREAF_IMAGE']
    scatteredness = halflight_radius**2/isoareaf
    high_scatteredness = (sigma_clip(scatteredness).mask) & (number > 0)
    
    large = (sigma_clip(isoareaf,sigma=4).mask) & (number > 0)
    ellipticity = reduced_csv['ELLIPTICITY']
    not_elliptical = (ellipticity < 0.5)
    fifthlight_radius = reduced_csv['FLUX_RADIUS_20']
    not_concentrated = ~sigma_clip(halflight_radius/fifthlight_radius,sigma_upper=3,sigma_lower=np.inf).mask & (number > 0)

    mask_csv = csv[above_analysis_thresh | high_fluxmax | (high_background | ~high_scatteredness) & ~(large & not_elliptical & not_concentrated) | (aperture_data_incomplete & ~flagswin_eight)]
    mask_csv.to_csv(filt_dir/f'{signature}_mask_{photfilt}.csv',index=False)
    mask = np.isin(segmap,mask_csv['NUMBER'])  

    return mask

def source_extractor_call(mask_params,sex_dir,filt_dir,photfilt,signature):
    data_path = filt_dir/f'{signature}_1a_data_{photfilt}.fits'
    weight_path = filt_dir/f'{signature}_1b_weight_{photfilt}.fits'
    detect_minarea = mask_params[0]
    detect_thresh = mask_params[1]
    subprocess.call(f"source-extractor {data_path} -c mask.sex -WEIGHT_IMAGE {weight_path} -DETECT_MINAREA {detect_minarea} -DETECT_THRESH {detect_thresh} -CHECKIMAGE_NAME {filt_dir/f'{signature}_2a_segmap_{photfilt}.fits'} -CATALOG_NAME {filt_dir/f'{signature}_segmap_{photfilt}.catalog'}", shell=True, cwd=sex_dir)
    with fits.open(filt_dir/f'{signature}_2a_segmap_{photfilt}.fits') as hdul:
        segmap = hdul[0].data
        
    return segmap

def get_csv(filt_dir,photfilt,signature):
    cat = pd.read_table(filt_dir/f'{signature}_segmap_{photfilt}.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','X_IMAGE','Y_IMAGE','FWHM_IMAGE','FLUX_ISO','FLUX_APER5','FLUX_APER25','FLUX_MAX','FLUX_AUTO','FLUX_WIN','ISOAREA_IMAGE','ISOAREAF_IMAGE','FLUX_RADIUS_20','FLUX_RADIUS_50','FLUX_RADIUS_90','ELLIPTICITY','A_IMAGE','BACKGROUND','XMIN_IMAGE','YMIN_IMAGE','XMAX_IMAGE','YMAX_IMAGE','XPEAK_IMAGE','YPEAK_IMAGE','X2_IMAGE','Y2_IMAGE','FLAGS','FLAGS_WIN']
    cat.to_csv(filt_dir/f'{signature}_segmap_{photfilt}.csv',index=False,header=header)
    os.remove(filt_dir/f'{signature}_segmap_{photfilt}.catalog')
    csv = pd.read_csv(filt_dir/f'{signature}_segmap_{photfilt}.csv')

    return csv

def get_background(sex_dir,filt_dir,photfilt,signature):
    '''
    If the background image is not satisfactory, you can try playing with the BACKSIZE parameter in the background.sex file.
    '''
    data_path = filt_dir/f'{signature}_1a_data_{photfilt}.fits'
    weight_path = filt_dir/f'{signature}_1b_weight_{photfilt}.fits'
    subprocess.call("source-extractor {0} -c background.sex -WEIGHT_IMAGE {1} -CHECKIMAGE_NAME {2}".format(data_path,weight_path,filt_dir/f'{signature}_1c_background_{photfilt}.fits'), shell=True, cwd=sex_dir)
    with fits.open(filt_dir/f'{signature}_1c_background_{photfilt}.fits') as hdul:
        background = hdul[0].data

    return background

def mask_image(filt_dir,photfilt,sex_dir,mask_params,signature,verbose):

    t1 = time.perf_counter()
    background = get_background(sex_dir,filt_dir,photfilt,signature)
    segmap = source_extractor_call(mask_params,sex_dir,filt_dir,photfilt,signature)
    csv = get_csv(filt_dir,photfilt,signature)
    mask = filter_segmap(segmap, csv, filt_dir, photfilt, signature)
    dilation_rad = 5
    dilated_mask = dilate_mask(mask,dilation_rad)
    hot_pixels_mask = get_hot_pixels_mask(filt_dir,photfilt,signature,dilated_mask)
    masked_data, combined_mask = apply_masks(filt_dir,photfilt,signature,dilated_mask,hot_pixels_mask,background)
    t2 = time.perf_counter()
    if verbose:
        print(f"masking {photfilt}: {t2-t1}")

    fits.writeto(filt_dir/f'{signature}_2a_segmap_{photfilt}.fits',segmap,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2b_filtered_{photfilt}.fits',mask.astype(int),overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2c_dialated_{photfilt}.fits',dilated_mask.astype(int),overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2d_hot_pixels_{photfilt}.fits',hot_pixels_mask.astype(int),overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2e_combined_mask_{photfilt}.fits',combined_mask.astype(int),overwrite=True)
    fits.writeto(filt_dir/f'{signature}_3_masked_data_{photfilt}.fits',masked_data,overwrite=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Filename of the original image.')
    parser.add_argument('segmap', help='Filename of the segmentation image.')
    parser.add_argument('max_dilations', type=int, help='Number of iterations for the mask booster.')
    parser.add_argument('verbose', default=False, help='Displays images and messages')
    parser.add_argument('save', default=False, help='Whether or not to save the image.')

    args = parser.parse_args()
    filename = args.data
    segmap = args.segmap
    max_dilations = args.max_dilations
    verbose = args.verbose
    save = args.save

    mask_image(filename,segmap,max_dilations,verbose,save)


    '''
    legacy code

    def iterative_mean_calculator(data,mask,filt_dir,signature):
    nandata = data.copy()
    nandata[mask] = np.nan
    radius = 30
    c1 = uniform_filter(nandata, radius*2, mode='nearest', origin=-radius)
    c2 = uniform_filter(nandata*nandata, radius*2, mode='nearest', origin=-radius)
    std = ((c2 - c1*c1)**.5)[:-radius*2+1,:-radius*2+1]
    mean = c1
    
    fits.writeto(filt_dir/f'{signature}_nandata.fits',nandata,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_std.fits',std,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_mean.fits',mean,overwrite=True)
    
    def apply_mask2(data,seg_bright,filt_dir,photfilt,signature):

    nanimg = data.copy()
    nanimg[seg_bright>0] = np.nan

    brightobject_params = pd.read_csv(filt_dir/f'{signature}_2c_segment_bright_{photfilt}.csv')

    a = (brightobject_params['A_IMAGE']*brightobject_params['KRON_RADIUS']).to_numpy()
    b = (brightobject_params['B_IMAGE']*brightobject_params['KRON_RADIUS']).to_numpy()
    theta = (np.radians(brightobject_params['THETA_IMAGE'])).to_numpy()
    x0 = (brightobject_params['X_IMAGE']).to_numpy()
    y0 = (brightobject_params['Y_IMAGE']).to_numpy()

    A = (a*sin(theta))**2+(b*cos(theta))**2
    B = 2*(b**2-a**2)*sin(theta)*cos(theta)
    C = (a*cos(theta))**2+(b*sin(theta))**2
    D = -2*A*x0-B*y0
    E = -B*x0-2*C*y0
    F = A*x0**2+B*x0*y0+C*y0**2-(a*b)**2

    (ymax, xmax) = data.shape
    y,x = np.mgrid[0:ymax,0:xmax]

    for i in range(brightobject_params.shape[0]):
        print(i)
        apermask = (A[i]*x**2+B[i]*x*y+C[i]*y**2+D[i]*x+E[i]*y+F[i])<0
        apervals = nanimg[apermask]
        meanaper = np.nanmean(apervals)
        stdaper = np.nanstd(apervals)
        fillsize = (seg_bright==i+1).sum()
        fill = np.random.normal(meanaper,0.75*stdaper,size=fillsize)
        data[seg_bright==i+1] = fill
    
    def create_mask(filt_dir,photfilt,signature,sex_dir):
    with fits.open(filt_dir/f'{signature}_2b_segmap_surf_{photfilt}.fits') as hdul:
        seg_surf = hdul[0].data
    with fits.open(filt_dir/f'{signature}_2a_segmap_deep_{photfilt}.fits') as hdul:
        seg_deep = hdul[0].data
    brightobj_ids = np.unique(seg_deep[seg_surf>0])
    brightobj_mask = np.isin(seg_deep,brightobj_ids)
    brightobj_seg = np.zeros(seg_deep.shape)
    brightobj_seg[brightobj_mask] = seg_deep[brightobj_mask]+100
    brightobj_path = filt_dir/f'{signature}_2bz_segment_bright_undetected_{photfilt}.fits'
    fits.writeto(brightobj_path,brightobj_seg,overwrite=True)
    subprocess.call(f"source-extractor {brightobj_path} -c mask.sex -CHECKIMAGE_NAME {filt_dir/f'{signature}_2c_segment_bright_{photfilt}.fits'} -CATALOG_NAME {filt_dir/f'{signature}_2c_segment_bright_{photfilt}.catalog'}", shell=True, cwd=sex_dir)
    det = pd.read_table(filt_dir/f'{signature}_2c_segment_bright_{photfilt}.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','X_IMAGE','Y_IMAGE','A_IMAGE','B_IMAGE','THETA_IMAGE','KRON_RADIUS']
    det.to_csv(filt_dir/f'{signature}_2c_segment_bright_{photfilt}.csv',index=False,header=header)
    os.remove(filt_dir/f'{signature}_2c_segment_bright_{photfilt}.catalog')

    with fits.open(filt_dir/f'{signature}_2c_segment_bright_{photfilt}.fits') as hdul:
        seg_bright = hdul[0].data

    return seg_surf, seg_deep, seg_bright

    
    '''