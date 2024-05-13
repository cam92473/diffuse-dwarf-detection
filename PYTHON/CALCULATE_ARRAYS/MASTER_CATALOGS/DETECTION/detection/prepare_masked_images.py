import numpy as np
from astropy.io import fits
from pathlib import Path
import time
import argparse

def get_global_extrema(output_root,phot_filters,signature):
    extrema = []
    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        masked_path = filt_dir/f'{signature}_3_data_masked_{photfilt}.fits'
        with fits.open(masked_path) as hdul:
            data = hdul[0].data
        extrema.append(data.min())
        extrema.append(data.max())
    sorted_extrema = sorted(extrema)
    global_min = sorted_extrema[0]
    global_max = sorted_extrema[-1]

    return (global_min, global_max)

def prepare_masked_images_for_gimp(output_root,phot_filters,signature,verbose):
    t1 = time.perf_counter()
    global_extrema = get_global_extrema(output_root,phot_filters,signature)
    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        masked_path = filt_dir/f'{signature}_3_data_masked_{photfilt}.fits'
        with fits.open(masked_path) as hdul:
            data = hdul[0].data
        data[0,0] = global_extrema[0]
        data[-1,-1] = global_extrema[1]
        fits.writeto(masked_path,data,overwrite=True)

    t2 = time.perf_counter()
    if verbose:
        print(f"preparing masked images: {t2-t1}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('filename', help='Filename of the data image, including the .fits extension.')
    parser.add_argument('windowindowsize', type=int, help='Window (bin) sizes for the pixels. The image is divided into square windows and the median of the pixels within each window is written to a single pixel in the output image. Supply this argument as the sidelength of the desired square window. More than one window sidelength can be provided, and for each ')
    parser.add_argument('dolog', default=True)
    parser.add_argument('testonimage', default=False, help='Set to true if you are testing this on a non-fits image.')
    parser.add_argument('verbose', default=True)
    parser.add_argument('wheresave', default=None)

    args = parser.parse_args()
    filename = args.filename
    windowindowsize = args.windowindowsize
    dolog = args.dolog
    testonimage = args.testonimage
    verbose = args.verbose
    wheresave = args.wheresave

    prepare_masked_images_for_gimp(filename,windowindowsize,dolog,testonimage,verbose,wheresave)