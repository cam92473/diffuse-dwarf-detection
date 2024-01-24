import numpy as np
from astropy.modeling.models import Sersic2D
from numpy import radians
from scipy.signal import fftconvolve
from astropy.convolution import convolve, convolve_fft
import matplotlib.pyplot as plt
import argparse
import time

def create_convolve_dwarfs(data,data_shape,Ieffs,reffs,ns,axisratios,thetas,x0s,y0s,num_dwarfs,r99s,psfkernel,convolve,diagnostic_images,verbose):

    thetas_rad = radians(thetas+90)
    ellipticities = 1 - axisratios

    #try putting all the new dwarfs in a zero image (tray), "baking" (convolving) the entire tray, and then plopping the results onto the original image

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
        print("creating Sersic profiles and putting them onto the tray (stickers)")
        t1 = time.perf_counter()

    for i in range(num_dwarfs):
        if verbose:
            print(f"dwarf #{i+1}")
        #sticker coords for dwarf i
        xxi, yyi = np.meshgrid(np.arange(sticker_leftedges[i],sticker_rightedges[i]),np.arange(sticker_bottomedges[i],sticker_topedges[i]))
        #Sersic profile for dwarf i
        modeli = Sersic2D(amplitude=Ieffs[i], r_eff=reffs[i], n=ns[i], x_0=x0s[i], y_0=y0s[i], ellip=ellipticities[i], theta=thetas_rad[i])
        #applying model to sticker coords to get a sticker
        if verbose:
            print("done making model")
        stickeri = modeli(xxi, yyi)
        if verbose:
            print("done assigning model to sticker")
        #putting sticker on the tray
        tray[sticker_bottomedges[i]:sticker_topedges[i],sticker_leftedges[i]:sticker_rightedges[i]] += stickeri
        if verbose:
            print("done putting sticker on tray")
    if verbose:
        t2 = time.perf_counter()
        print(f"tray filling time: {t2-t1}")

    if diagnostic_images:
        plt.imshow(np.log10(tray+1))
        plt.title("log image of sticker-filled tray")
        plt.show()

    if convolve:
        if verbose:
            print("convolving dwarfs (this could take a while)")
            t1 = time.perf_counter()
        conv_tray = fftconvolve(tray,psfkernel,mode='same')
        if verbose:
            t2 = time.perf_counter()
            print(f"convolution time: {t2-t1}")
    else:
        print("note: not convolving")
        conv_tray = tray
    
    if diagnostic_images:
        plt.imshow(np.log10(conv_tray+1))
        plt.title("log image of convolved tray")
        plt.show()

    if verbose:
        print("adding tray to image")
        t1 = time.perf_counter()
    data += conv_tray
    if verbose:
        t2 = time.perf_counter()
        print(f"adding tray time: {t2-t1}")

    if diagnostic_images:
        fig, ax = plt.subplots()
        logdata = np.log10(data-data.min()+1)
        #the vmin and vmax parameters here are arbitrary
        im = ax.imshow(logdata, vmin=1, vmax=logdata.max()*0.5)
        cbar = fig.colorbar(im,ax=ax)
        plt.title("log image of data after convolved tray has been placed on top")
        plt.show()

    return data

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