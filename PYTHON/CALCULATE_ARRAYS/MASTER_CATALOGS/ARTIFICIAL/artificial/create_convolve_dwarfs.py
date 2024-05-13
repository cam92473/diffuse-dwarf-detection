import numpy as np
from astropy.modeling.models import Sersic2D
from numpy import radians
from scipy.signal import fftconvolve
from astropy.convolution import convolve, convolve_fft
import matplotlib.pyplot as plt
import argparse
import time

def create_convolve_dwarfs(data,data_shape,Ieffs,reffs,ns,axisratios,thetas,x0s,y0s,num_dwarfs,r99s,psfkernel,subtract,verbose):

    thetas_rad = radians(thetas+90)
    ellipticities = 1 - axisratios

    #the dwarfs are created and convolved on stickers which are designed to be just big enough to contain pretty much the entire profile of the dwarf.
    #in addition to being added to the data image, the dwarfs will be added to a tray containing the data only in the sticker regions. In other words, outside the stickers, the values are all zero. This is simply for diagnostic purposes (to see the locations of the new artificial dwarfs)

    tray = np.zeros(data_shape)

    #specifying coordinates of the stickers. Stickers close to the edge need to have their coordinates cropped.

    sticker_leftedges = (x0s-r99s).astype(int)
    sticker_leftedges[sticker_leftedges<0] = 0
    sticker_rightedges = (x0s+r99s).astype(int)
    sticker_rightedges[sticker_rightedges>(data_shape[1]-1)] = data_shape[1]-1
    sticker_bottomedges = (y0s-r99s).astype(int)
    sticker_bottomedges[sticker_bottomedges<0] = 0
    sticker_topedges = (y0s+r99s).astype(int)
    sticker_topedges[sticker_topedges>(data_shape[0]-1)] = data_shape[0]-1

    if verbose:
        print("creating artificial dwarf profiles...")
        t1 = time.perf_counter()

    for i in range(num_dwarfs):
        if verbose:
            print(f"dwarf #{i+1}")
        #sticker coords for dwarf i
        xxi, yyi = np.meshgrid(np.arange(sticker_leftedges[i],sticker_rightedges[i]),np.arange(sticker_bottomedges[i],sticker_topedges[i]))
        #Sersic profile for dwarf i
        modeli = Sersic2D(amplitude=Ieffs[i], r_eff=reffs[i], n=ns[i], x_0=x0s[i], y_0=y0s[i], ellip=ellipticities[i], theta=thetas_rad[i])
        #applying model to sticker coords to get a sticker
        stickeri = modeli(xxi, yyi)
        if psfkernel is not None:
            conv_stickeri = fftconvolve(stickeri,psfkernel,mode='same')
        else:
            conv_stickeri = stickeri
        tray[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]] = data[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]]
        if not subtract:
            data[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]] += conv_stickeri
            tray[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]] += conv_stickeri
        else:
            data[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]] -= conv_stickeri
            tray[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]] -= conv_stickeri

    if verbose:
        t2 = time.perf_counter()
        print(f"done creating artificial dwarf profiles. Total time: {t2-t1}")

    return data, tray

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('filename', help='Filename of the image to which the dwarfs will be added.')
    parser.add_argument('-psf', help='Filename of the PSF with which to convolve the dwarfs.')
    parser.add_argument('-num_dwarfs', type=int, help='The number of dwarfs to be added to the image.')
    parser.add_argument('-mag', type=float, nargs='+', help='List of apparent magnitudes of the dwarfs.')
    parser.add_argument('-reff', type=float, nargs='+', help='List of effective or half-light radii, in pixels, of the dwarfs.')
    parser.add_argument('-n', type=float, nargs='+', help='List of sersic indices of the dwarfs.')
    parser.add_argument('-axisratio', type=float, nargs='+', help='List of axis ratios of the dwarfs. Note: axis ratio = 1 - ellipticity. (an axis ratio of 1 describes a radially-symmetric dwarf)')
    parser.add_argument('-theta', type=float, nargs='+', help='List of rotation angles of the dwarfs, in degrees.')
    parser.add_argument('-x0', type=float, nargs='+', help='List of x positions of the dwarfs, in pixels.')
    parser.add_argument('-y0', type=float, nargs='+', help='List of y positions of the dwarfs, in pixels.')
    parser.add_argument('-verbose', action='store_true', default=False, help='If toggled, gives diagnostic command-line messages.')
    args = parser.parse_args()

    filename = args.filename
    psf = args.psf
    num_dwarfs = args.num_dwarfs
    mag = np.asarray(args.mag)
    reff = np.asarray(args.reff)
    n = np.asarray(args.n)
    x0 = np.asarray(args.x0)
    y0 = np.asarray(args.y0)
    axisratio = np.asarray(args.axisratio)
    theta = np.asarray(args.theta)
    verbose = args.verbose

    #create_dwarfs(filename,psf,num_dwarfs,mag,reff,n,axisratio,theta,x0,y0,verbose)

        #sticker_left[sticker_left<0] = 0
    #sticker_right[sticker_right>(data_shape[1]-1)] = data_shape[1]-1
    #sticker_bottom[sticker_bottom<0] = 0
    #sticker_top[sticker_top>(data_shape[0]-1)] = data_shape[0]-1
        #xx, yy = np.meshgrid(np.arange(data_shape[1]),np.arange(data_shape[0]))
    '''
    
    I0 = np.zeros(num_dwarfs)

    for i in range(num_dwarfs):
        if verbose:
            print(f"dwarf #{i+1}")
        model = Sersic2D(amplitude=Ieffs[i], r_eff=reffs[i], n=ns[i], x_0=x0s[i], y_0=y0s[i], ellip=ellipticities[i], theta=thetas_rad[i])
        sticker_x, sticker_y = np.meshgrid(np.arange(sticker_left[i],sticker_right[i]+1), np.arange(sticker_bottom[i],sticker_top[i]+1), copy=False)
        sticker = model(sticker_x,sticker_y)
        I0[i] = np.max(sticker)
        conv_sticker = fftconvolve(sticker, psfkernel, mode='same')
        data[sticker_y,sticker_x] += conv_sticker'''