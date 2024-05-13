import numpy as np
import argparse
from astropy.io import fits
import time
import bottleneck as bn

def stack_blurred_images(output_root, phot_filters, signature, verbose):

    t1 = time.perf_counter()

    binnedlist = []

    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        with fits.open(filt_dir/f'{signature}_4_blurred_{photfilt}.fits') as hdul:
            binned_data = hdul[0].data
            binnedlist.append(binned_data)

    binnedstack = np.asarray(binnedlist)
    stacked = bn.nanmin(binnedstack,axis=0)
    
    t2 = time.perf_counter()
    if verbose:
        print(f"stacking: {t2-t1}")

    fits.writeto(output_root/f'{signature}_5_stacked.fits',stacked,overwrite=True)
    

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

    stack_blurred_image(filename,windowindowsize,dolog,testonimage,verbose,wheresave)