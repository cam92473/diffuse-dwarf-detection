import numpy as np
from astropy.io import fits
import argparse
import time
import subprocess
import pandas as pd
import os
from scipy.ndimage import binary_dilation

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

def apply_mask(data,mask,background):
    noise = np.random.normal(0,0.5*np.nanstd(data[~mask]),size=data.shape)
    data[mask] = background[mask] + noise[mask]

    return data

def create_brightobj_mask(segmap_surf,segmap_deep,deep_csv):
    flags_win = deep_csv['FLAGS_WIN']
    flags_win_mask = ~(flags_win>8)
    no_win_ids = deep_csv['NUMBER'][flags_win_mask]
    no_win_mask = np.isin(segmap_deep,no_win_ids)
    brightobj_ids = np.unique(segmap_deep[segmap_surf>0])
    brightobj_mask = np.isin(segmap_deep,brightobj_ids)
    combined_mask = no_win_mask & brightobj_mask

    return combined_mask

def create_star_mask(segmap_star,star_csv):
    isoareaf = star_csv['ISOAREAF_IMAGE']
    flags = star_csv['FLAGS']
    meansize = np.mean(isoareaf)
    stdsize = np.std(isoareaf)
    area_mask = isoareaf < meansize + 5*stdsize
    flag_mask = ~((flags==2) | (flags==3) | (flags==18) | (flags==19)) #these flags indicate deblended objects with possibly incomplete aperture data
    star_mask = area_mask & flag_mask
    star_ids = star_csv['NUMBER'][star_mask]
    star_mask = np.isin(segmap_star,star_ids)
    dilated_star_mask = dilate_mask(star_mask,5)

    return dilated_star_mask

def get_brightobj_segmaps(data_path,weight_path,surf_params,deep_params,sex_dir,filt_dir,photfilt,signature):
    surf_minarea = surf_params[0]
    surf_thresh = surf_params[1]
    deep_minarea = deep_params[0]
    deep_thresh = deep_params[1]
    subprocess.call(f"source-extractor {data_path} -c segmentation.sex -WEIGHT_IMAGE {weight_path} -DETECT_MINAREA {surf_minarea} -DETECT_THRESH {surf_thresh} -CHECKIMAGE_NAME {filt_dir/f'{signature}_2a_segmap_surf_{photfilt}.fits'}", shell=True, cwd=sex_dir)
    subprocess.call(f"source-extractor {data_path} -c segmentation.sex -WEIGHT_IMAGE {weight_path} -DETECT_MINAREA {deep_minarea} -DETECT_THRESH {deep_thresh} -CHECKIMAGE_NAME {filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.fits'} -CATALOG_NAME {filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.catalog'}", shell=True, cwd=sex_dir)
    with fits.open(filt_dir/f'{signature}_2a_segmap_surf_{photfilt}.fits') as hdul:
        segmap_surf = hdul[0].data
    with fits.open(filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.fits') as hdul:
        segmap_deep = hdul[0].data

    deep_cat = pd.read_table(filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','X_IMAGE','Y_IMAGE','FLAGS_WIN']
    #seems silly to read cat, delete cat, write csv, and read csv
    deep_cat.to_csv(filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.csv',index=False,header=header)
    os.remove(filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.catalog')
    deep_csv = pd.read_csv(filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.csv')
        
    return segmap_surf, segmap_deep, deep_csv

def get_star_segmap(data_path,weight_path,star_params,sex_dir,filt_dir,photfilt,signature):
    star_minarea = star_params[0]
    star_thresh = star_params[1]
    subprocess.call(f"source-extractor {data_path} -c star.sex -WEIGHT_IMAGE {weight_path} -DETECT_MINAREA {star_minarea} -DETECT_THRESH {star_thresh} -CHECKIMAGE_NAME {filt_dir/f'{signature}_2e_segmap_star_{photfilt}.fits'} -CATALOG_NAME {filt_dir/f'{signature}_2e_segmap_star_{photfilt}.catalog'}", shell=True, cwd=sex_dir)
    star_cat = pd.read_table(filt_dir/f'{signature}_2e_segmap_star_{photfilt}.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','X_IMAGE','Y_IMAGE','ISOAREAF_IMAGE','FLAGS']
    #seems silly to read cat, delete cat, write csv, and read csv
    star_cat.to_csv(filt_dir/f'{signature}_2e_segmap_star_{photfilt}.csv',index=False,header=header)
    os.remove(filt_dir/f'{signature}_2e_segmap_star_{photfilt}.catalog')
    star_csv = pd.read_csv(filt_dir/f'{signature}_2e_segmap_star_{photfilt}.csv')
    with fits.open(filt_dir/f'{signature}_2e_segmap_star_{photfilt}.fits') as hdul:
        segmap_star = hdul[0].data
        
    return segmap_star, star_csv

def get_background(data_path,weight_path,sex_dir,filt_dir,photfilt,signature):
    '''
    If the background image is not satisfactory, you can try playing with the BACKSIZE parameter in the background.sex file.
    '''
    subprocess.call("source-extractor {0} -c background.sex -WEIGHT_IMAGE {1} -CHECKIMAGE_NAME {2}".format(data_path,weight_path,filt_dir/f'{signature}_1c_background_{photfilt}.fits'), shell=True, cwd=sex_dir)
    with fits.open(filt_dir/f'{signature}_1c_background_{photfilt}.fits') as hdul:
        background = hdul[0].data

    return background

def mask_image(filt_dir,photfilt,sex_dir,surf_params,deep_params,star_params,signature,verbose):

    '''
    Mask out objects that are definitively not dwarfs before performing the median filtering. This makes things easier when identifying potential dwarfs in the
    median-filtered image. Dwarfs are large and faint, so we want to get rid of objects that are large and not faint, as well as small objects (point sources). The first mask
    throws out all objects above a certain brightness threshold using sextractor's DETECT_THRESH. Ideally this threshold corresponds to slightly above the brightest
    dwarf. Of course, the entire object including the wings must be thrown out, which means that two passes of sextractor's detection algorithm are required; one for
    identifying the bright objects (a surface scan) and a deep scan that has such a low DETECT_THRESH that it uncovers essentially everything in the image. The entire
    extent, as revealed by the deep scan, of those objects in the surface scan, are then discarded via the first mask. The second mask encompasses all objects that
    are small and reasonably bright. The previous deep scan is too deep for this, as lots of junky specks are picked up as objects, so we have to do a third sextractor run, 
    not so deep that we pick up specks and random junk (which might be part of dwarfs), but deep enough we get all of the stars. This scan may well detect dwarfs since there is
    no control over the size of objects detected by sextractor. Fortunately we can prevent these from becoming part of the mask by filtering the catalog-turned-csv
    that sextractor spits out. The detections in the csv, filtered by size to ensure they are stars only, are the contents of the second mask. Applying both masks to
    the data in succession thus removes bright extended objects as well as stars. The replacement value of the mask is simply the background with some added Gaussian noise.
    This is both fast and makes a surprisingly good filler, so that the image post-masking looks as though the objects we removed were simply never there in the first place.
    '''

    t1 = time.perf_counter()

    data_path = filt_dir/f'{signature}_1a_data_{photfilt}.fits'
    weight_path = filt_dir/f'{signature}_1b_weight_{photfilt}.fits'
    background = get_background(data_path,weight_path,sex_dir,filt_dir,photfilt,signature)
    with fits.open(data_path) as hdul:
        data = hdul[0].data

    segmap_surf, segmap_deep, deep_csv = get_brightobj_segmaps(data_path,weight_path,surf_params,deep_params,sex_dir,filt_dir,photfilt,signature)
    brightobj_mask = create_brightobj_mask(segmap_surf,segmap_deep, deep_csv)
    data_brightobj_masked = apply_mask(data,brightobj_mask,background)
    masked_path = filt_dir/f'{signature}_2d_brightobj_masked_{photfilt}.fits'
    fits.writeto(masked_path,data_brightobj_masked,overwrite=True)

    segmap_star, star_csv = get_star_segmap(masked_path,weight_path,star_params,sex_dir,filt_dir,photfilt,signature)
    star_mask = create_star_mask(segmap_star, star_csv)
    data_masked = apply_mask(data_brightobj_masked,star_mask,background)

    #segmap_surf[segmap_surf>0] = 1
    #segmap_deep[segmap_deep>0] = 1
    #segmap_star[segmap_star>0] = 1

    combined_mask = brightobj_mask | star_mask
    segmap_masked = segmap_deep.copy()
    segmap_masked[combined_mask] = 0

    t2 = time.perf_counter()
    if verbose:
        print(f"masking {photfilt}: {t2-t1}")


    fits.writeto(filt_dir/f'{signature}_2a_segmap_surf_{photfilt}.fits',segmap_surf,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2b_segmap_deep_{photfilt}.fits',segmap_deep,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2c_brightobj_mask_{photfilt}.fits',brightobj_mask.astype(int),overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2e_segmap_star_{photfilt}.fits',segmap_star,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2f_star_mask_{photfilt}.fits',star_mask.astype(int),overwrite=True)
    fits.writeto(filt_dir/f'{signature}_2h_segmap_deep_masked_{photfilt}.fits',segmap_masked,overwrite=True)
    fits.writeto(filt_dir/f'{signature}_3_data_masked_{photfilt}.fits',data_masked,overwrite=True)

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