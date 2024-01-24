import argparse
import numpy as np
import time
from datetime import datetime
from pathlib import Path

from MATCH_CATALOG.get_match_catalog import get_match_catalog
from plot_completion import make_plot

def create_array(pixeldirs,num_rows,num_cols,signature):

    completion_array = np.zeros((num_rows,num_cols))

    for r in range(num_rows):
        for c in range(num_cols):
            p = r*num_cols+c
            with open(pixeldirs[p]/f'{signature}_master_artificial_dwarfs.catalog') as inputcat:
                inputlines = inputcat.readlines()
                num_input_dwarfs = len(inputlines)-1
            with open(pixeldirs[p]/f'{signature}_master_matches.catalog') as matchcat:
                matchlines = matchcat.readlines()
                num_match_dwarfs = len(matchlines)-1
            completion_array[r,c] = num_match_dwarfs/num_input_dwarfs*100

    return completion_array

def build_completion_array(data, weight, phot_filter, mag_bin_vals, reff_bin_vals, n_range, axisratio_range, theta_range, num_dwarfs, psf, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, num_runs, clean, diagnostic_images, verbose, outdir, sexdir, saveimdir, signature):

    if verbose:
        print("Starting to build completion array")
        t1 = time.perf_counter()

    mag_bins = np.arange(mag_bin_vals[0],mag_bin_vals[1]+mag_bin_vals[2],mag_bin_vals[2])
    reff_bins = np.arange(reff_bin_vals[0],reff_bin_vals[1]+reff_bin_vals[2],reff_bin_vals[2])
    num_rows = reff_bins.size-1
    num_cols = mag_bins.size-1

    pixeldirs = []

    for r in range(num_rows):
        for c in range(num_cols):
            mag_range = [mag_bins[c], mag_bins[c+1]]
            reff_range = [reff_bins[r], reff_bins[r+1]]
            pixeldir = Path(outdir/f'mag{mag_range[0]}-{mag_range[1]}'/f'reff{reff_range[0]}-{reff_range[1]}')
            pixeldir.mkdir(parents=True,exist_ok=True)
            pixeldirs.append(pixeldir)
            get_match_catalog(data, weight, phot_filter, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, psf, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, num_runs, clean, diagnostic_images, verbose, pixeldir, sexdir, signature)

    completion_array = create_array(pixeldirs,num_rows,num_cols,signature)
    np.savetxt(outdir/f"{signature}_completion.arr",completion_array,header=f"{mag_bin_vals[0]} {mag_bin_vals[1]} {mag_bin_vals[2]} {reff_bin_vals[0]} {reff_bin_vals[1]} {reff_bin_vals[2]}")
    
    if verbose:
        t2 = time.perf_counter()
        print(f"finished building completion array and saved to output directory. Total time: {t2-t1}")

    savename = saveimdir/f"{signature}_completion.png"
    make_plot(mag_bins,reff_bins,num_rows,num_cols,completion_array,savename)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path of the data image, including the .fits extension.')
    parser.add_argument('weight', help='Path of the weight image, including the .fits extension.')
    parser.add_argument('phot_filter', choices=['u','g','r','i','z'], help='The photometric filter the data was taken in. This is needed to apply the correct zero point magnitude.')
    parser.add_argument('mag_bin_vals', nargs=3, type=float, help='A set of three numbers for creating the bins for the magnitude parameter: <start> <stop(inclusive)> <step>.')
    parser.add_argument('reff_bin_vals', nargs=3, type=float, help='A set of three numbers for creating the bins for the effective radius parameter: <start> <stop(inclusive)> <step>.')
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
    mag_bin_vals = args.mag_bin_vals
    reff_bin_vals = args.reff_bin_vals
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
    root = Path.cwd().parents[1]
    outdir = Path(root/'OUTPUT'/signature)
    outdir.mkdir(parents=True,exist_ok=True)
    sexdir = Path(root/'PYTHON'/'COMPLETION'/'MASTER_CATALOG'/'DETECTION'/'sextractor')
    saveimdir = Path(root/'RESULTS'/'completion_plots')

    build_completion_array(data, weight, phot_filter, mag_bin_vals, reff_bin_vals, n_range, axisratio_range, theta_range, num_dwarfs, psf, obj_params, maxdilations, maskfunc, windowsize, dolog, det_params, sigclip, num_runs, clean, diagnostic_images, verbose, outdir, sexdir, saveimdir, signature)