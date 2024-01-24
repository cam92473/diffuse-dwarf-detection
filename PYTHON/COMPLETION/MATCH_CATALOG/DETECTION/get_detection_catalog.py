import argparse
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

def create_segmentation_map(data, weight, obj_params, sexdir, outdir, signature, verbose):
    obj_minarea = obj_params[0]
    obj_thresh = obj_params[1]
    if verbose:
        print("creating segmentation map with sextractor...")
        t1 = time.perf_counter()
    subprocess.call(f"source-extractor {data} -c getobjects.sex -DETECT_MINAREA {obj_minarea} -DETECT_THRESH {obj_thresh} -WEIGHT_IMAGE {weight} -CHECKIMAGE_NAME {outdir/f'{signature}_segment_objs.fits'}", shell=True, cwd=sexdir)
    if verbose:
        t2 = time.perf_counter()
        print(f"segmentation map creation time: {t2-t1}")

def scan_binned_image(det_params, sexdir, outdir, signature, verbose):
    det_minarea = det_params[0]
    det_thresh = det_params[1]
    if verbose:
        print("getting raw detections with sextractor...")
        t1 = time.perf_counter()
    subprocess.call(f"source-extractor {outdir/f'{signature}_binned.fits'} -c getdetections.sex -DETECT_MINAREA {det_minarea} -DETECT_THRESH {det_thresh} -CHECKIMAGE_NAME {outdir/f'{signature}_segment_dets.fits'} -CATALOG_NAME {outdir/f'{signature}_filtered_detections.catalog'}", shell=True, cwd=sexdir)
    if verbose:
        t2 = time.perf_counter()
        print(f"detection time: {t2-t1}")

def create_catalog(outdir,signature,verbose):
    if verbose:
        print("creating detections catalog...")
        t1 = time.perf_counter()
    header = f"{'#NUMBER':>10s}{'ALPHA_J2000':>12s}{'DELTA_J2000':>12s}{'FLUX_RAD':>11s}{'MAG_AUTO':>9s}{'MAGERR':>9s}{'X_IMAGE':>12s}{'Y_IMAGE':>12s}{'ELLIP':>9s}{'STAR':>7s}{'SNR_WIN':>11s}{'MAG_APR1':>9s}{'MAG_APR2':>9s}{'MAG_APR3':>9s}{'MAG_APR4':>9s}"
    with open(outdir/f'{signature}_filtered_detections.catalog', 'r+') as f:
        content = f.read()
        f.seek(0,0)
        f.write(header + '\n' + content)
        f.close()
    if verbose:
        t2 = time.perf_counter()
        print(f"creating catalog time: {t2-t1}")

def clean_up_files(outdir, signature, verbose):
    if verbose:
        print("cleaning up unneeded files...")
        t1 = time.perf_counter()
    os.remove(outdir/f'{signature}_segment_objs.fits')
    os.remove(outdir/f'{signature}_masked.fits')
    os.remove(outdir/f'{signature}_binned.fits')
    os.remove(outdir/f'{signature}_segment_dets.fits')
    if verbose:
        t2 = time.perf_counter()
        print(f"cleaning time: {t2-t1}")

def get_detection_catalog(data, weight, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, clean, diagnostic_images, verbose, outdir, sexdir, signature):
    create_segmentation_map(data, weight, obj_params, sexdir, outdir, signature, verbose)
    mask_image(data, outdir, maxdilations, maskfunc, diagnostic_images, signature, verbose)
    bin_image(outdir, windowsize, dolog, False, diagnostic_images, signature, verbose)
    scan_binned_image(det_params, sexdir, outdir, signature, verbose)
    create_catalog(outdir, signature, verbose)
    #filter_table(outdir/'detections.catalog', sig_beneath, sig_right, verbose, outdir/'dwarf_candidates.fits')
    if clean:
        clean_up_files(outdir, signature, verbose)
    if verbose:
        print("finished detection algorithm")

if __name__ == '__main__':

    from detection.bin_image import bin_image
    from detection.mask_image import mask_image
    from detection.filter_table import filter_table

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path of the data image, including the .fits extension.')
    parser.add_argument('weight', help='Path of the weight image, including the .fits extension.')
    parser.add_argument('-obj_params', nargs=2, default=[10,30], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used to generate the segmentation image which later gets turned into a mask.')
    parser.add_argument('-maxdilations', default=10, type=int, help='Maximum number of times to binary dilate the objects in the sextractor-output segmentation image, with each of the diamond and square kernels. In other words, the largest objects will be dialated (twice) this many times. The number of dialations an object undergoes depends on its size, using the function specified.')
    parser.add_argument('-maskfunc', type=str, choices=['sinh','expsq'], default='expsq', help='Function used to calculate the mask size distribution according to object size. Choices are sinh and expsq. sinh avoids masking smaller objects; expsq with too high a maxdilation may cause masking of dwarfs. Default is expsq.')
    parser.add_argument('-windowsize', default=10, type=int, help='Size of the window used to bin the pixels in the masked image. The image is divided into square windows having the specified sidelength. The median of the pixels within each window is written to a single pixel in the output image.')
    parser.add_argument('-dolog', type=int, default=1, help='Whether or not the binned image is log normalized. Specify 1 for True or 0 for False. Default is 1.')
    parser.add_argument('-det_params', nargs=2, default=[5,1], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used when performing detection on the binned image to obtain the raw (unfiltered) detections.')
    parser.add_argument('-sigclip', nargs=2, type=float, default=[1.05,2.5], help='Number of standard deviations the kappa sigma clippers use to filter the raw detections. The first argument is the number of standard devations beneath the fitted exponential (in MAG_AUTO vs. FLUX_RAD). The second refers to the number of standard deviations to the right of the mean flux value.')
    parser.add_argument('--clean', action='store_true', default=False, help='Deletes output images and files (except, of course, the catalog) after the program has completed. This is useful for saving memory if you do not need to look at the files afterwards.')
    parser.add_argument('--diagnostic_images', action='store_true', default=False, help='Displays diagnostic images from time to time. These images can be useful but interrupt the program and require the user to not be AFK. They also reduce the speed of the program somewhat.')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    weight = Path(args.weight).resolve()
    obj_params = args.obj_params
    maxdilations = args.maxdilations
    maskfunc = args.maskfunc
    windowsize = args.windowsize
    dolog = bool(args.dolog)
    det_params = args.det_params
    sigclip = args.sigclip
    clean = args.clean
    diagnostic_images = args.diagnostic_images
    verbose = args.verbose

    timestr = datetime.now().strftime("-%Y%m%d%H%M%S")
    filenamestr = data.name.split('.')[0]
    signature = filenamestr + timestr
    root = Path.cwd().parents[3]
    outdir = Path(root/'OUTPUT'/signature)
    outdir.mkdir(parents=True,exist_ok=True)
    sexdir = Path(root/'PYTHON'/'COMPLETION'/'MASTER_CATALOG'/'DETECTION'/'sextractor')  

    get_detection_catalog(data, weight, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, clean, diagnostic_images, verbose, outdir, sexdir, signature)

else:
    from .detection.bin_image import bin_image
    from .detection.mask_image import mask_image
    from .detection.filter_table import filter_table