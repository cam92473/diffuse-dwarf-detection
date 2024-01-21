from DETECTION.python.detection_algorithm import detection_algorithm
from ARTIFICIAL.insert_dwarfs import insert_dwarfs
from COMPLETION.create_match_catalog import create_match_catalog
from COMPLETION.combine_catalogs import combine_catalogs
from COMPLETION.produce_completion_plot import produce_completion_plot
import os
import time
import argparse
from pathlib import Path
from datetime import datetime
#from ddd.combine_catalogues import combine_catalogues
#from ddd.completion import completion

def clean(outdir, verbose):
    if verbose:
        print("cleaning up unneeded images...")
        t1 = time.perf_counter()
    os.remove(outdir/'data_filled.fits')
    os.remove(outdir/'segment_objs.fits')
    os.remove(outdir/'masked.fits')
    os.remove(outdir/'binned.fits')
    os.remove(outdir/'segment_dets.fits')
    if verbose:
        t2 = time.perf_counter()
        print(f"cleaning time: {t2-t1}")

def main(data, weight, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, num_runs, clean, verbose, plots):

    mag_range = [mag_range[0], mag_range[1]]
    reff_range = [reff_range[0], reff_range[1]]
    n_range = [n_range[0], n_range[1]]
    axisratio_range = [axisratio_range[0], axisratio_range[1]]
    theta_range = [theta_range[0], theta_range[1]]
    #n_range = [1, 1]
    #axisratio_range = [0.5, 1] 
    #theta_range = [0, 360]

    maxdilation = 9
    windowsize = 50
    obj_minarea = 5
    obj_thresh = 20
    maskfunc = 'linear'
    dw_minarea = 1
    dw_thresh = 0.5
    dolog = 1
    sig_beneath = 1.05
    sig_right = 2

    filenamestr = data.name.split('.')[0]
    timestr = datetime.now().strftime("-%Y%m%d%H%M%S")

    for run_no in range(num_runs):
        outdir = Path(f"~/Desktop/dwarf_detection/OUTPUT/{filenamestr+timestr}/mag{str(mag_range)}/reff{str(reff_range)}/{filenamestr+timestr+'-'+run_no}")
        outdir.mkdir(parents=True)

        insert_dwarfs(data, windowsize, num_dwarfs, mag_range, reff_range, n_range, axisratio_range, theta_range, verbose, outdir)
        detection_algorithm(outdir/'data_filled.fits',weight,maxdilation,windowsize,obj_minarea,obj_thresh,maskfunc,dw_minarea,dw_thresh,dolog,sig_beneath,sig_right,verbose)
        if clean:
            clean(outdir,verbose)
        create_match_catalog(outdir/'artificial_dwarfs.catalog',outdir/'filtered_detections.catalog',outdir/'matches.catalog',verbose)
    combine_catalogs(outdir.parent,num_runs,verbose)
    produce_completion_plot(outdir)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path of the science image containing the real dwarf galaxies.')
    parser.add_argument('weight', help='Path of the weight image associated with the data image, used in SExtractor to help with detections.')
    parser.add_argument('mag_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the apparent magnitude of the artificial dwarfs.')
    parser.add_argument('reff_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the effective radius of the artificial dwarfs. reff, the effective radius, is the radial distance inside of which half of the light of the dwarf is contained. reff and n are used to calculate the other two Sersic parameters, I0 and bn.')
    parser.add_argument('n_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the Sersic index n of the artificial dwarfs. Lower values of n correspond to profiles where the light is more centrally concentrated. reff and n are used to calculate the other two Sersic parameters, I0 and bn.')
    parser.add_argument('axisratio_range', nargs=2, type=float, help='Two numbers (low and high) that specify the axis ratio range of the artificial dwarfs. The axis ratio takes a value from 0 to 1, where 0 is unphysical and 1 is perfectly circular. (It is the complement of the ellipticity)')
    parser.add_argument('theta_range', nargs=2, type=float, help='Two numbers (low and high) that specify the angular offset range of artificial dwarfs, in degrees. Enter 0 and 360 if you want to include all possible angles.')
    parser.add_argument('num_dwarfs', type=int, help='number of dwarfs')
    parser.add_argument('num_runs', type=int, help='number of runs')
    parser.add_argument('-clean', action='store_true', default=False, help='Whether at the end of each run to clean up the images that are used by the program. If you want to keep and inspect these images, do not provide this argument. Note however that several images are produced each run with about the same size as the original data image you input, and so, if you are using a large image, not providing this argument may cause a large amount of disk space to be consumed, especially if you are doing more than a couple of runs.')
    parser.add_argument('-verbose', action='store_true', default=False, help='Whether to display messages on the console as the program works. These messages indicate what task the program is currently working on as well as how long the last task took.')
    parser.add_argument('-plots', action='store_true', default=False, help='Whether to display plots at certain points. These plots are useful for seeing what the program is doing, but displaying these plots comes with a downside; namely, that the execution of the program is halted whenever a plot is shown. The user must manually close the window containing the plot in order for the program to resume. This is undesirable if the user simply wants to let the program run for a long time in an unsupervised manner.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    weight = Path(args.weight).resolve()
    weight = args.weight
    mag_range = args.mag_range
    reff_range = args.reff_range
    n_range = args.n_range
    axisratio_range = args.axisratio_range
    theta_range = args.theta_range
    num_dwarfs = args.num_dwarfs
    num_runs = args.num_runs
    clean = args.clean
    verbose = args.verbose
    plots = args.plots

    main(data,weight,mag_range,reff_range,n_range,axisratio_range,theta_range,num_dwarfs,num_runs,clean,verbose,plots)