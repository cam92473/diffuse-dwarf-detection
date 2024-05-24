import subprocess
import time
import argparse
from pathlib import Path
import pandas as pd
import os
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clip

def filter_detections(output_root,csv,csv_fold,segmap,signature,verbose):

    t1 = time.perf_counter()

    flags = csv['FLAGS']
    flagswin = csv['FLAGS_WIN']
    flagged = (flags >= 16) | (flagswin > 8)

    reduced_csv = csv[~flagged]
    number = reduced_csv['NUMBER']

    isoarea = reduced_csv['ISOAREA_IMAGE']
    large = isoarea >= np.percentile(isoarea,90)
    #large = sigma_clip(isoarea,sigma=3).mask & (number > 0)

    snrwin = reduced_csv['SNR_WIN']
    #high_flux = sigma_clip(snrwin,sigma=3.5,maxiters=1).mask & (number > 0)
    bright = snrwin >= np.percentile(snrwin,90)

    ellipticity = reduced_csv['ELLIPTICITY']
    round = (ellipticity <= 0.4)

    fluxmax = reduced_csv['FLUX_MAX']
    #high_sb = sigma_clip(fluxmax,sigma=4,maxiters=1).mask & (number > 0)
    #bright_pixels = fluxmax > np.percentile(fluxmax,90)

    halflight_radius = reduced_csv['FLUX_RADIUS']
    scatteredness = halflight_radius**2/isoarea
    not_scattered = scatteredness < np.percentile(scatteredness,20)

    filtered_csv = csv[~flagged & round]
    filtered_csv.to_csv(csv_fold/f'{signature}_filtered_detections.csv',index=False)

    mask = np.isin(segmap,filtered_csv['NUMBER'])
    filtered_detections = segmap.copy()
    filtered_detections[~mask] = 0
    fits.writeto(output_root/f'{signature}_7_filtered_detections.fits',filtered_detections,overwrite=True)

    t2 = time.perf_counter()
    if verbose:
        print(f"filtering objects: {t2-t1}")


def source_extractor_call(output_root,sex_dir,detect_params,signature,verbose):
    t1 = time.perf_counter()
    detect_minarea = detect_params[0]
    detect_thresh = detect_params[1]
    subprocess.call(f"source-extractor {output_root/f'{signature}_5_stacked.fits'} -c detect.sex -DETECT_MINAREA {detect_minarea} -DETECT_THRESH {detect_thresh} -ANALYSIS_THRESH {detect_thresh} -CHECKIMAGE_NAME {output_root/f'{signature}_6_raw_detections.fits'} -CATALOG_NAME {output_root/f'{signature}_raw_detections.catalog'}", shell=True, cwd=sex_dir)
    with fits.open(output_root/f'{signature}_6_raw_detections.fits') as hdul:
        segmap = hdul[0].data
    t2 = time.perf_counter()
    if verbose:
        print(f'detecting objects: {t2-t1}')

    return segmap

def get_csv(output_root,signature):
    cat = pd.read_table(output_root/f'{signature}_raw_detections.catalog',sep='\s+',escapechar='#', header=None)
    header = ['NUMBER','ALPHA_J2000','DELTA_J2000','X_IMAGE','Y_IMAGE','FLUX_RADIUS','MAG_AUTO','MAGERR_AUTO','FLUX_ISO','FLUXERR_ISO','MAG_ISO','MAGERR_ISO','FLUX_ISOCOR','FLUXERR_ISOCOR','MAG_ISOCOR','MAGERR_ISOCOR','FLUX_WIN','MAG_WIN','SNR_WIN','FLUX_GROWTH','FLUX_GROWTHSTEP','ELLIPTICITY','CLASS_STAR','BACKGROUND','FLUX_MAX','ISOAREA_IMAGE','XPEAK_IMAGE','YPEAK_IMAGE','XMIN_IMAGE','YMIN_IMAGE','XMAX_IMAGE','YMAX_IMAGE','XPEAK_FOCAL','YPEAK_FOCAL','X_FOCAL','Y_FOCAL','X2_IMAGE','Y2_IMAGE','CXX_IMAGE','CYY_IMAGE','CXY_IMAGE','CXXWIN_IMAGE','CYYWIN_IMAGE','CXYWIN_IMAGE','FLAGS','FLAGS_WIN','ISO0','ISO1','ISO2','ISO3','ISO4','ISO5','ISO6','ISO7','FWHM_IMAGE']
    csv_fold = output_root/'csv'
    csv_fold.mkdir(exist_ok=True,parents=True)
    cat.to_csv(csv_fold/f'{signature}_raw_detections.csv',index=False,header=header)
    os.remove(output_root/f'{signature}_raw_detections.catalog')
    csv = pd.read_csv(csv_fold/f'{signature}_raw_detections.csv')
    
    return csv, csv_fold

def detect_objects(output_root, sex_dir, detect_params, signature, verbose):

    segmap = source_extractor_call(output_root,sex_dir,detect_params,signature,verbose)
    csv, csv_fold = get_csv(output_root,signature)
    filter_detections(output_root,csv,csv_fold,segmap,signature,verbose)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('output_root', help='')
    parser.add_argument('sex_dir', help='')
    parser.add_argument('-detect_params', nargs=2, default=[10,5], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used when performing detection on the binned image to obtain the raw (unfiltered) detections.')
    parser.add_argument('signature', help='')
    parser.add_argument('--verbose', action='store_true', default=False, help='')

    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    sex_dir = Path(args.sex_dir).resolve()
    detect_params = args.detect_params
    signature = args.signature
    verbose = args.verbose

    get_blurred_detections(output_root,sex_dir,detect_params,signature,verbose)


    '''
    LEGACY CODE

    def photometry_filter2(det,csv_fold,signature):
    magauto = det['MAG_AUTO']
    magauto_clip = sigma_clip(magauto,sigma=10,masked=False)
    magmean = np.mean(magauto_clip)
    mag_too_large = magauto > magmean
    snrwin = det['SNR_WIN']
    flux_too_small = snrwin < np.percentile(snrwin,80)
    det[mag_too_large].to_csv(csv_fold/f'{signature}_26_mag_too_large.csv',index=False)
    det[flux_too_small].to_csv(csv_fold/f'{signature}_27_flux_too_small.csv',index=False)
    photometry_mask = mag_too_large | flux_too_small
    #photometry_rejects = det[~photometry_mask]
    #photometry_rejects.to_csv(csv_fold/f'{signature}_photometry_rejects.csv',index=False)

    return photometry_mask

def morphology_filter(det,csv_fold,signature):
    ellipticity = det['ELLIPTICITY']
    high_ellipticity = ellipticity > 0.4
    conc = det['MAG_APER4']-det['MAG_APER1']
    conc_clip = sigma_clip(conc,masked=False)
    conc_mean = np.mean(conc_clip)
    conc_std = np.std(conc_clip)
    concentration_far_from_mean = (conc < conc_mean-conc_std) | (conc > conc_mean+conc_std)
    isophotal_area = det['ISOAREA_IMAGE']
    area_too_small = isophotal_area < np.percentile(isophotal_area,80)
    x, y = det['X_IMAGE'], det['Y_IMAGE']
    xpeak, ypeak = det['XPEAK_IMAGE'], det['YPEAK_IMAGE']
    xmin, ymin = det['XMIN_IMAGE'], det['YMIN_IMAGE']
    xmax, ymax = det['XMAX_IMAGE'], det['YMAX_IMAGE']
    lopsidedness = ((x-xpeak)**2+(y-ypeak)**2)/((xmax-xmin)**2+(ymax-ymin)**2)
    lopsided = (lopsidedness > np.percentile(lopsidedness,75))
    x_variance = det['X2_IMAGE']
    y_variance = det['Y2_IMAGE']
    profile_too_sharp = (x_variance < np.percentile(x_variance,75)) | (y_variance < np.percentile(y_variance,75))
    iso7 = det['ISO7']
    iso6 = det['ISO6']
    iso5 = det['ISO5']
    iso4 = det['ISO4']
    iso3 = det['ISO3']
    iso2 = det['ISO2']
    iso1 = det['ISO1']
    iso0 = det['ISO0']
    isoareas = np.array([iso0,iso1,iso2,iso3,iso4,iso5,iso6,iso7]).T
    isoareas_decrease = np.zeros((isoareas.shape[0],1))
    for i in range(isoareas.shape[0]):
        isoareas_decrease[i] = np.unique(isoareas[i]).size
    sudden_isoarea_decrease = pd.Series((isoareas_decrease < 4).flatten())

    det[high_ellipticity].to_csv(csv_fold/f'{signature}_20_high_ellipticity.csv',index=False)
    det[concentration_far_from_mean].to_csv(csv_fold/f'{signature}_21_concentration_far_from_mean.csv',index=False)
    det[area_too_small].to_csv(csv_fold/f'{signature}_22_area_too_small.csv',index=False)
    det[lopsided].to_csv(csv_fold/f'{signature}_23_lopsided.csv',index=False)
    det[profile_too_sharp].to_csv(csv_fold/f'{signature}_24_profile_too_sharp.csv',index=False)
    det[sudden_isoarea_decrease].to_csv(csv_fold/f'{signature}_25_sudden_isoarea_decrease.csv',index=False)
    morphology_mask = high_ellipticity | concentration_far_from_mean | area_too_small | lopsided | profile_too_sharp | sudden_isoarea_decrease
    #morphology_rejects = det[~morphology_mask]
    #morphology_rejects.to_csv(csv_fold/f'{signature}_morphology_rejects.csv',index=False)

    return morphology_mask

def junk_filter(det,csv_fold,signature):
    negative_snrwin = det['SNR_WIN']<0
    negative_fluxgrowth = det['FLUX_GROWTH']<0
    star_outlier = ~np.isclose(det['CLASS_STAR'],0.056)
    bg = det['BACKGROUND']
    bg_outlier = ((bg<np.percentile(bg,1)) | (bg>np.percentile(bg,99)))
    flags = det['FLAGS']
    flag_neighbours = flags==1
    flag_blended = flags==2
    flag_neighbours_blended = flags==3
    flag_aperture = flags==16
    flag_aperture_neighbours = flags==17
    flag_aperture_blended = flags==18
    flag_aperture_neighbours_blended = flags==19
    flag_aperture_truncated = flags==24
    flag_aperture_truncated_neighbours = flags==25
    flag_aperture_truncated_blended = flags==26
    flag_aperture_truncated_neighbours_blended = flags==27
    flags_win = det['FLAGS_WIN']
    flag_win_3 = flags_win==3
    flag_win_7 = flags_win==7
    flag_win_8 = flags_win==8
    flag_win_11 = flags_win==11
    junk_mask = negative_snrwin | negative_fluxgrowth | star_outlier | bg_outlier | flag_neighbours | flag_blended | flag_neighbours_blended | flag_aperture | flag_aperture_neighbours | flag_aperture_blended | flag_aperture_neighbours_blended | flag_aperture_truncated | flag_aperture_truncated_neighbours | flag_aperture_truncated_blended | flag_aperture_truncated_neighbours_blended | flag_win_3 | flag_win_7 | flag_win_8 | flag_win_11
    #junk_rejects = det[~junk_mask] 
    #junk_rejects.to_csv(csv_fold/f'{signature}_junk_rejects.csv',index=False)
    
    det[negative_snrwin].to_csv(csv_fold/f'{signature}_1_negative_snrwin.csv',index=False)
    det[negative_fluxgrowth].to_csv(csv_fold/f'{signature}_2_negative_fluxgrowth.csv',index=False)
    det[star_outlier].to_csv(csv_fold/f'{signature}_3_star_outlier.csv',index=False)
    det[bg_outlier].to_csv(csv_fold/f'{signature}_4_bg_outlier.csv',index=False)
    det[flag_neighbours].to_csv(csv_fold/f'{signature}_5_flag_neighbours.csv',index=False)
    det[flag_blended].to_csv(csv_fold/f'{signature}_6_flag_blended.csv',index=False)
    det[flag_neighbours_blended].to_csv(csv_fold/f'{signature}_7_flag_neighbours_blended.csv',index=False)
    det[flag_aperture].to_csv(csv_fold/f'{signature}_8_flag_aperture.csv',index=False)
    det[flag_aperture_neighbours].to_csv(csv_fold/f'{signature}_9_flag_aperture_neighbours.csv',index=False)
    det[flag_aperture_blended].to_csv(csv_fold/f'{signature}_10_flag_aperture_blended.csv',index=False)
    det[flag_aperture_neighbours_blended].to_csv(csv_fold/f'{signature}_11_flag_aperture_neighbours_blended.csv',index=False)
    det[flag_aperture_truncated].to_csv(csv_fold/f'{signature}_12_flag_aperture_truncated.csv',index=False)
    det[flag_aperture_truncated_neighbours].to_csv(csv_fold/f'{signature}_13_flag_aperture_truncated_neighbours.csv',index=False)
    det[flag_aperture_truncated_blended].to_csv(csv_fold/f'{signature}_14_flag_aperture_truncated_blended.csv',index=False)
    det[flag_aperture_truncated_neighbours_blended].to_csv(csv_fold/f'{signature}_15_flag_aperture_truncated_neighbours_blended.csv',index=False)
    det[flag_win_3].to_csv(csv_fold/f'{signature}_16_flag_win3.csv',index=False)
    det[flag_win_7].to_csv(csv_fold/f'{signature}_17_flag_win7.csv',index=False)
    det[flag_win_8].to_csv(csv_fold/f'{signature}_18_flag_win8.csv',index=False)
    det[flag_win_11].to_csv(csv_fold/f'{signature}_19_flag_win11.csv',index=False)

    return junk_mask
    '''