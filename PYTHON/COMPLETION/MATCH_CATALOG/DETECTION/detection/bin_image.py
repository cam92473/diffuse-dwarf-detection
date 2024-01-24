from matplotlib import pyplot as plt
from astropy.io import fits
import numpy as np
from numpy import log10
import argparse
from matplotlib.image import imread, imsave
from modest_image import imshow as modest_imshow
import time

def lognormalize(img):
    min = np.nanmin(img)
    if min <= 0:
        img -= (min-1)
    return log10(img)

def bin_image(outdir, windowsize, dolog, testonimage, diagnostic_images, signature, verbose):

    if verbose:
        t1 = time.perf_counter()

    if testonimage:
        data = imread(outdir/f'{signature}_masked.fits')
        if len(data.shape) == 3:
            r, c, _ = data.shape
        else:
            r, c = data.shape 
        origin = 'upper'
    else:
        with fits.open(outdir/f'{signature}_masked.fits') as hdul:
            primary_hdu = hdul[0]
            header = primary_hdu.header
            data = primary_hdu.data
            r, c = data.shape
        origin = 'lower'

    if diagnostic_images:
        _, ax = plt.subplots(figsize=(20,20))
        modest_imshow(ax, data, cmap='gray', interpolation='none', origin=origin)
        plt.show()

    num_windows_r = r//windowsize
    remaining_pixels_r = r%windowsize
    num_windows_c = c//windowsize
    remaining_pixels_c = c%windowsize
    trimmed = data[:-remaining_pixels_r or None,:-remaining_pixels_c or None]
    
    windows = trimmed.reshape(-1,windowsize,num_windows_c,windowsize).swapaxes(1,2).reshape(-1,windowsize,windowsize)
    median_image = np.median(windows,axis=(1,2)).reshape(num_windows_r,num_windows_c)

    if dolog:
        median_image = lognormalize(median_image)

    if diagnostic_images:
        ax = plt.gca()
        modest_imshow(ax, median_image, cmap='gray', interpolation='none', origin=origin)
        plt.show()

    if testonimage:
        imsave(outdir/f'{signature}_binned.fits',median_image)
    else:
        fits.writeto(outdir/f'{signature}_binned.fits',median_image,header,overwrite=True)

    if verbose:
        t2 = time.perf_counter()
        print(f"binning time: {t2-t1}")

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

    bin_image(filename,windowindowsize,dolog,testonimage,verbose,wheresave)

    '''
    LEGACY CODE
    
    r_binned = r//windowsize
    c_binned = c//windowsize
    rcoords = np.arange(0,r_binned+1)*windowsize
    ccoords = np.arange(0,c_binned+1)*windowsize

    median_image = np.zeros((r_binned, c_binned))

    if verify:
        print("binning image")
    for r in range(r_binned):
        if verify:
            print(r)
        for c in range(c_binned):
            median_image[r,c] = np.median(data[rcoords[r]:rcoords[r+1],ccoords[c]:ccoords[c+1]])'''