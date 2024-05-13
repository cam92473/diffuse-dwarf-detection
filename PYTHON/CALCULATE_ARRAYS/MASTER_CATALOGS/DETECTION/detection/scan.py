import subprocess
import time
import argparse
from pathlib import Path
import pandas as pd
import os

def scan_stacked_image(output_root, sex_dir, det_params, signature, verbose):
    t1 = time.perf_counter()
    det_minarea = det_params[0]
    det_thresh = det_params[1] 
    subprocess.call(f"source-extractor {output_root/f'{signature}_5_stacked.fits'} -c getdetections.sex -DETECT_MINAREA {det_minarea} -DETECT_THRESH {det_thresh} -CHECKIMAGE_NAME {output_root/f'{signature}_6_raw_detections.fits'} -CATALOG_NAME {output_root/f'{signature}_raw_detections.catalog'}", shell=True, cwd=sex_dir)
    det = pd.read_table(output_root/f'{signature}_raw_detections.catalog',sep='\s+',escapechar='#', header=None)
    #header = ['NUMBER','ALPHA_J2000','DELTA_J2000','MAG_AUTO','X_IMAGE','Y_IMAGE','ELLIP','STAR','SNR_WIN','MAG_APER1','MAG_APER2','MAG_APER3','MAG_APER4','BACKGROUND','CXXWIN_IMAGE','CYYWIN_IMAGE','FLUX_GROWTH']
    header = ['NUMBER','ALPHA_J2000','DELTA_J2000','X_IMAGE','Y_IMAGE','FLUX_RADIUS','MAG_AUTO','MAGERR_AUTO','FLUX_ISO','FLUXERR_ISO','MAG_ISO','MAGERR_ISO','FLUX_ISOCOR','FLUXERR_ISOCOR','MAG_ISOCOR','MAGERR_ISOCOR','FLUX_WIN','MAG_WIN','SNR_WIN','MAG_APER1','MAG_APER2','MAG_APER3','MAG_APER4','FLUX_GROWTH','FLUX_GROWTHSTEP','ELLIPTICITY','CLASS_STAR','BACKGROUND','FLUX_MAX','ISOAREA_IMAGE','XPEAK_IMAGE','YPEAK_IMAGE','XMIN_IMAGE','YMIN_IMAGE','XMAX_IMAGE','YMAX_IMAGE','XPEAK_FOCAL','YPEAK_FOCAL','X_FOCAL','Y_FOCAL','X2_IMAGE','Y2_IMAGE','CXX_IMAGE','CYY_IMAGE','CXY_IMAGE','CXXWIN_IMAGE','CYYWIN_IMAGE','CXYWIN_IMAGE','FLAGS','FLAGS_WIN','ISO0','ISO1','ISO2','ISO3','ISO4','ISO5','ISO6','ISO7','FWHM_IMAGE']
    csv_fold = output_root/'csv'
    csv_fold.mkdir(exist_ok=True,parents=True)
    det.to_csv(csv_fold/f'{signature}_0_raw_detections.csv',index=False,header=header)
    os.remove(output_root/f'{signature}_raw_detections.catalog')
    t2 = time.perf_counter()
    if verbose:
        print(f"detection: {t2-t1}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('output_root', help='')
    parser.add_argument('sex_dir', help='')
    parser.add_argument('-det_params', nargs=2, default=[10,5], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used when performing detection on the binned image to obtain the raw (unfiltered) detections.')
    parser.add_argument('signature', help='')
    parser.add_argument('--verbose', action='store_true', default=False, help='')

    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    sex_dir = Path(args.sex_dir).resolve()
    det_params = args.det_params
    signature = args.signature
    verbose = args.verbose

    scan_stacked_image(output_root,sex_dir,det_params,signature,verbose)