import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

def create_segmentation_map(data, weight_params, obj_params, sexdir, outdir, signature, verbose):
    obj_minarea = obj_params[0]
    obj_thresh = obj_params[1]
    weight_type = weight_params[0]
    weight_image = weight_params[1]
    if verbose:
        print("creating segmentation map with sextractor...")
        t1 = time.perf_counter()
    #subprocess.call(f"source-extractor {data} -c getobjects.sex -DETECT_MINAREA {obj_minarea} -DETECT_THRESH {obj_thresh} -WEIGHT_TYPE {weight_type} -WEIGHT_IMAGE {weight_image} -CHECKIMAGE_NAME {chr(34)+str(outdir/f'{signature}_segment_objs.fits')+', '+str(outdir/f'{signature}_background_objs.fits')+', '+str(outdir/f'{signature}_backgroundrms_objs.fits')+', '+str(outdir/f'{signature}_apertures_objs.fits')+', '+str(outdir/f'{signature}_objects_objs.fits')+', '+str(outdir/f'{signature}_minusbg_objs.fits')+', '+str(outdir/f'{signature}_minusobjs_objs.fits')+chr(34)}", shell=True, cwd=sexdir)
    subprocess.call(f"source-extractor {data} -c getobjects.sex -DETECT_MINAREA {obj_minarea} -DETECT_THRESH {obj_thresh} -WEIGHT_TYPE {weight_type} -WEIGHT_IMAGE {weight_image} -CHECKIMAGE_NAME {outdir/f'{signature}_segment_objs.fits'}", shell=True, cwd=sexdir)
    if verbose:
        t2 = time.perf_counter()
        print(f"segmentation map creation time: {t2-t1}")

def scan_binned_image(det_params, sexdir, outdir, signature, verbose):
    det_minarea = det_params[0]
    det_thresh = det_params[1]
    if verbose:
        print("getting raw detections with sextractor...")
        t1 = time.perf_counter()
    #subprocess.call(f"source-extractor {outdir/f'{signature}_binned.fits'} -c getdetections.sex -DETECT_MINAREA {det_minarea} -DETECT_THRESH {det_thresh} -CHECKIMAGE_NAME {chr(34)+str(outdir/f'{signature}_segment_dets.fits')+', '+str(outdir/f'{signature}_background_dets.fits')+', '+str(outdir/f'{signature}_backgroundrms_dets.fits')+', '+str(outdir/f'{signature}_apertures_dets.fits')+', '+str(outdir/f'{signature}_objects_dets.fits')+', '+str(outdir/f'{signature}_minusbg_dets.fits')+', '+str(outdir/f'{signature}_minusobjs_dets.fits')+chr(34)} -CATALOG_NAME {outdir/f'{signature}_filtered_detections.catalog'}", shell=True, cwd=sexdir)
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

def get_detection_catalog(data, weight_params, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, gallery, verbose, outdir, sexdir, signature):
    if verbose:
        print("Starting detection algorithm...")
        ts = time.perf_counter()
    create_segmentation_map(data, weight_params, obj_params, sexdir, outdir, signature, verbose)
    mask_image(data, outdir, maxdilations, maskfunc, signature, verbose)
    bin_image(outdir, windowsize, dolog, False, signature, verbose)
    scan_binned_image(det_params, sexdir, outdir, signature, verbose)
    create_catalog(outdir, signature, verbose)
    #filter_table(outdir/'detections.catalog', sig_beneath, sig_right, verbose, outdir/'dwarf_candidates.fits')
    if verbose:
        tf = time.perf_counter()
        print(f"Finished detection algorithm. Total time: {tf-ts}")
    if gallery:
        if verbose:
            print("displaying gallery...")
        plot_detection_gallery(data,outdir,None)

if __name__ == '__main__':

    from detection.bin_image import bin_image
    from detection.mask_image import mask_image
    from detection.filter_table import filter_table
    from plot_detection_gallery import plot_detection_gallery

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path of the data image, including the .fits extension.')
    parser.add_argument('weight', help='Path of the weight image, including the .fits extension. If you do not want to use a weight image, enter NO-WEIGHT.')
    parser.add_argument('-obj_params', nargs=2, default=[10,30], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used to generate the segmentation image which later gets turned into a mask.')
    parser.add_argument('-maxdilations', default=10, type=int, help='Maximum number of times to binary dilate the objects in the sextractor-output segmentation image, with each of the diamond and square kernels. In other words, the largest objects will be dialated (twice) this many times. The number of dialations an object undergoes depends on its size, using the function specified.')
    parser.add_argument('-maskfunc', type=str, choices=['sinh','expsq'], default='expsq', help='Function used to calculate the mask size distribution according to object size. Choices are sinh and expsq. sinh avoids masking smaller objects; expsq with too high a maxdilation may cause masking of dwarfs. Default is expsq.')
    parser.add_argument('-windowsize', default=10, type=int, help='Size of the window used to bin the pixels in the masked image. The image is divided into square windows having the specified sidelength. The median of the pixels within each window is written to a single pixel in the output image.')
    parser.add_argument('-dolog', type=int, default=1, help='Whether or not the binned image is log normalized. Specify 1 for True or 0 for False. Default is 1.')
    parser.add_argument('-det_params', nargs=2, default=[5,1], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used when performing detection on the binned image to obtain the raw (unfiltered) detections.')
    parser.add_argument('-sigclip', nargs=2, type=float, default=[1.05,2.5], help='Number of standard deviations the kappa sigma clippers use to filter the raw detections. The first argument is the number of standard devations beneath the fitted exponential (in MAG_AUTO vs. FLUX_RAD). The second refers to the number of standard deviations to the right of the mean flux value.')
    parser.add_argument('--gallery', action='store_true', default=False, help='Displays a gallery of images at the end of the detection procedure. Useful for getting a visual understanding of what happens in the course of the algorithm, and is good for bug-spotting and doing a reality check.')
    parser.add_argument('--signature', help='Optional parameter which allows you to specify the signature, or the name used to identify the output folder and all of its files (if not specified, a name will be created based on the input data image and the current time).')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    if args.weight == 'NONE':
        weight_params = ['NONE','NONE']
    else:
        weight_params = ['MAP_WEIGHT',Path(args.weight).resolve()]
    obj_params = args.obj_params
    maxdilations = args.maxdilations
    maskfunc = args.maskfunc
    windowsize = args.windowsize
    dolog = bool(args.dolog)
    det_params = args.det_params
    sigclip = args.sigclip
    gallery = args.gallery
    signature = args.signature
    verbose = args.verbose

    timestr = datetime.now().strftime("-%Y%m%d%H%M%S")
    filenamestr = data.name.split('.')[0]
    if signature is None:
        signature = filenamestr + timestr
    root = Path.cwd().parents[3]
    outdir = Path(root/'OUTPUT'/signature)
    outdir.mkdir(parents=True,exist_ok=True)
    sexdir = Path(root/'PYTHON'/'COMPLETION'/'MATCH_CATALOG'/'DETECTION'/'sextractor')  

    get_detection_catalog(data, weight_params, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, gallery, verbose, outdir, sexdir, signature)

else:
    from .detection.bin_image import bin_image
    from .detection.mask_image import mask_image
    from .detection.filter_table import filter_table
    from .plot_detection_gallery import plot_detection_gallery