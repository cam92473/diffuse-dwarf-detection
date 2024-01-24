import argparse
import time
from datetime import datetime
from pathlib import Path

def get_match_catalog(data, weight, phot_filter, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, psf, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, num_runs, clean, diagnostic_images, verbose, outdir, sexdir, signature):

    '''maxdilation = 9
    windowsize = 50
    obj_minarea = 5
    obj_thresh = 20
    maskfunc = 'linear'
    dw_minarea = 1
    dw_thresh = 0.5
    dolog = 1
    sig_beneath = 1.05
    sig_right = 2'''

    if verbose:
        print(f"getting match catalog for {num_runs} runs of mag {mag_range[0]}-{mag_range[1]} & reff {reff_range[0]}-{reff_range[1]}")
        t1 = time.perf_counter()

    rundirs = []
    for run_no in range(num_runs):
        #rundir = Path(pixeldir/f'run_{run_no}')
        rundir = Path(outdir/f'run_{run_no}')
        rundir.mkdir(parents=True,exist_ok=True)
        rundirs.append(rundir)
        get_artificial_catalog(data, phot_filter, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, psf, windowsize, None, clean, diagnostic_images, verbose, rundir, signature)
        get_detection_catalog(rundir/f'{signature}_filled.fits', weight, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, clean, diagnostic_images, verbose, rundir, sexdir, signature)    
    create_master_catalogs(rundirs,num_runs,signature,verbose)
    tol = 2
    create_match_catalog(rundirs,num_runs,tol,signature,verbose)
    #create_match_catalog(rundir/f'{signature}_artificial_dwarfs.catalog',rundir/f'{signature}_filtered_detections.catalog',rundir/f'{signature}_matches.catalog',verbose)
    if verbose:
        t2 = time.perf_counter()
        print(f"finished getting match catalog. Total time: {t2-t1}")

if __name__ == "__main__":

    from DETECTION.get_detection_catalog import get_detection_catalog
    from ARTIFICIAL.get_artificial_catalog import get_artificial_catalog
    from catalog.create_match_catalog import create_match_catalog
    from catalog.create_master_catalogs import create_master_catalogs

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path of the data image, including the .fits extension.')
    parser.add_argument('weight', help='Path of the weight image, including the .fits extension.')
    parser.add_argument('phot_filter', choices=['u','g','r','i','z'], help='The photometric filter the data was taken in. This is needed to apply the correct zero point magnitude.')
    parser.add_argument('mag_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the apparent magnitude of the artificial dwarfs.')
    parser.add_argument('reff_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the effective radius of the artificial dwarfs. Provide these numbers in arcseconds. reff, the effective radius, is the radial distance inside of which half of the light of the dwarf is contained. reff and n are used to calculate the other two Sersic parameters, I0 and bn.')
    parser.add_argument('n_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the Sersic index n of the artificial dwarfs. Lower values of n correspond to profiles where the light is more centrally concentrated. reff and n are used to calculate the other two Sersic parameters, I0 and bn.')
    parser.add_argument('axisratio_range', nargs=2, type=float, help='Two numbers (low and high) that specify the axis ratio range of the artificial dwarfs. The axis ratio takes a value from 0 to 1, where 0 is unphysical and 1 is perfectly circular. (It is the complement of the ellipticity)')
    parser.add_argument('theta_range', nargs=2, type=float, help='Two numbers (low and high) that specify the angular offset range of artificial dwarfs, in degrees. Enter 0 and 360 if you want to include all possible angles.')
    parser.add_argument('num_dwarfs', type=int, help='The number of artificial dwarfs to insert into the data image.')
    parser.add_argument('psf', help='Path to the psf used to convolve the artificial dwarfs.')
    parser.add_argument('-obj_params', nargs=2, default=[10,30], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used to generate the segmentation image which later gets turned into a mask.')
    parser.add_argument('-maxdilations', default=10, type=int, help='Maximum number of times to binary dilate the objects in the sextractor-output segmentation image, with each of the diamond and square kernels. In other words, the largest objects will be dialated (twice) this many times. The number of dialations an object undergoes depends on its size, using the function specified.')
    parser.add_argument('-maskfunc', type=str, choices=['sinh','expsq'], default='expsq', help='Function used to calculate the mask size distribution according to object size. Choices are sinh and expsq. sinh avoids masking smaller objects; expsq with too high a maxdilation may cause masking of dwarfs. Default is expsq.')
    parser.add_argument('-windowsize', default=10, type=int, help='Size of the window used to bin the pixels in the masked image. The image is divided into square windows having the specified sidelength. The median of the pixels within each window is written to a single pixel in the output image.')
    parser.add_argument('-dolog', type=int, default=1, help='Whether or not the binned image is log normalized. Specify 1 for True or 0 for False. Default is 1.')
    parser.add_argument('-det_params', nargs=2, default=[5,1], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used when performing detection on the binned image to obtain the raw (unfiltered) detections.')
    parser.add_argument('-sigclip', nargs=2, type=float, default=[1.05,2.5], help='Number of standard deviations the kappa sigma clippers use to filter the raw detections. The first argument is the number of standard devations beneath the fitted exponential (in MAG_AUTO vs. FLUX_RAD). The second refers to the number of standard deviations to the right of the mean flux value.')
    parser.add_argument('num_runs', type=int, help='The number of times to construct artificial and detection catalogs using the same ranges of artificial dwarf parameters.')
    parser.add_argument('--clean', action='store_true', default=False, help='Deletes output images and files (except, of course, the catalog) after the program has completed. This is useful for saving memory if you do not need to look at the files afterwards.')
    parser.add_argument('--diagnostic_images', action='store_true', default=False, help='Displays diagnostic images from time to time. These images can be useful but interrupt the program and require the user to not be AFK. They also reduce the speed of the program somewhat.')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    weight = Path(args.weight).resolve()
    phot_filter = args.phot_filter
    mag_range = args.mag_range
    reff_range = args.reff_range
    n_range = args.n_range
    axisratio_range = args.axisratio_range
    theta_range = args.theta_range
    num_dwarfs = args.num_dwarfs
    psf = args.psf
    obj_params = args.obj_params
    maxdilations = args.maxdilations
    maskfunc = args.maskfunc
    windowsize = args.windowsize
    dolog = bool(args.dolog)
    det_params = args.det_params
    sigclip = args.sigclip
    num_runs = args.num_runs
    clean = args.clean
    diagnostic_images = args.diagnostic_images
    verbose = args.verbose

    timestr = datetime.now().strftime("-%Y%m%d%H%M%S")
    filenamestr = data.name.split('.')[0]
    signature = filenamestr + timestr
    root = Path.cwd().parents[2]
    outdir = Path(root/'OUTPUT'/signature)
    outdir.mkdir(parents=True,exist_ok=True)
    sexdir = Path(root/'PYTHON'/'COMPLETION'/'MATCH_CATALOG'/'DETECTION'/'sextractor')  

    get_match_catalog(data, weight, phot_filter, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, psf, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, num_runs, clean, diagnostic_images, verbose, outdir, sexdir, signature)

else:

    from .DETECTION.get_detection_catalog import get_detection_catalog
    from .ARTIFICIAL.get_artificial_catalog import get_artificial_catalog
    from .catalog.create_match_catalog import create_match_catalog
    from .catalog.create_master_catalogs import create_master_catalogs