import argparse
import numpy as np
import time
import json
import shutil
from datetime import datetime
import numpy as np
from numpy import exp, pi, log10
from pathlib import Path
from astropy.io import fits
from numpy.random import uniform, randint
from scipy.special import gamma, gammainc
from scipy.optimize import fsolve

def getzp(phot_filter):
    if phot_filter == 'u':
        zp = 0
        col='?'
    elif phot_filter == 'g':
        zp = 30
        col = 1
    elif phot_filter == 'r':
        zp = 0
        col=2
    elif phot_filter == 'i':
        zp = 0
        col=3
    elif phot_filter == 'z':
        zp = 0
        col=4
    return zp, col

def restofterms(reffs,ns,b_ns,axisratios):
    # 2 pi Reff^2 e^bn n bn^-2n gamma(2n) q
    return 2*pi*reffs**2*ns*exp(b_ns)*b_ns**(-2*ns)*gamma(2*ns)*axisratios

def bndefinition(b_n,n):
    #This is the REGULARIZED incomplete gamma function, hence the 1 (not gamma(2*n)). See scipy documentation
    return 1 - 2*gammainc(2*n,b_n)

def get_the_bn(n):
    root = fsolve(bndefinition,x0=[1.9992*n-0.3271],args=(n))
    return root[0]

def find_bns(ns,num_dwarfs,verbose):
    b_ns = np.zeros(num_dwarfs)
    if verbose:
        print("finding b_ns")
        t1 = time.perf_counter()
    for i in range(num_dwarfs):
        b_ns[i] = get_the_bn(ns[i])
    if verbose:
        t2 = time.perf_counter()
        print(f"finding b_ns time: {t2-t1}")
    return b_ns

def find_Ftots(mags,frpath,zp,col):
    fr = np.genfromtxt(frpath).T[col]
    fr = fr[(fr>0.01)]
    #print(fr)
    mean_fr = fr[fr!=0].mean()
    #print(mean_fr)
    F_tots = mean_fr*(10**(-0.4*(mags-zp)))
    return F_tots

def find_Ieffs(mags,reffs,ns,b_ns,axisratios,thetas,num_dwarfs,frpath,zp,col,verbose):
    F_tots = find_Ftots(mags,frpath,zp,col)
    Ieffs = F_tots/restofterms(reffs,ns,b_ns,axisratios)
    return Ieffs

def r999definition(r999,b_n,n,reff):
    #This is the REGULARIZED incomplete gamma function, hence the 0.999 (not 0.999*gamma(2*n)). See scipy documentation
    return 0.999 - gammainc(2*n,b_n*(r999/reff)**1/n)

def get_the_r999(b_n,n,reff):
    root = fsolve(r999definition,x0=[3*reff],args=(b_n,n,reff))
    return root[0]

def find_r999s(b_ns,ns,reffs,num_dwarfs,verbose):
    r999s = np.zeros(num_dwarfs)
    if verbose:
        print("finding r999s")
        t1 = time.perf_counter()
    for i in range(num_dwarfs):
        r999s[i] = get_the_r999(b_ns[i],ns[i],reffs[i])
    if verbose:
        t2 = time.perf_counter()
        print(f"finding r999s time: {t2-t1}")
    return r999s

def get_artificial_catalog(data, phot_filter, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, psf, windowsize, reff_units, positions, subtract, gallery, verbose, outdir, frpath, signature):
    
    #first convert reff_range to pix, if not already in pix
    res = 0.2637    # "/pix for DECam
    cenAdist = 3.8E6    # distance to NGC5128
    if reff_units == 'as':
        reff_range = [i/res for i in reff_range]
    elif reff_units == 'px':
        pass
    elif reff_units == 'pc':
        reff_range = [i/cenAdist*206265/res for i in reff_range]

    #get randomized parameters for dwarfs
    mags = uniform(mag_range[0],mag_range[1],size=num_dwarfs)
    reffs = uniform(reff_range[0],reff_range[1],size=num_dwarfs)
    ns = uniform(n_range[0],n_range[1],size=num_dwarfs)
    axisratios = uniform(axisratio_range[0],axisratio_range[1],size=num_dwarfs)
    thetas = uniform(theta_range[0],theta_range[1],size=num_dwarfs)

    #get image shape, needed for placing dwarfs (getting coords)
    with fits.open(data) as hdul:
        phdu = hdul[0]
        data1 = phdu.data
        header = phdu.header
        data1_shape = data1.shape

    #have to place the dwarfs on non-NaN coordinates, so we use the following code
    if positions is None:
        x0s = np.zeros(num_dwarfs,dtype=int)
        y0s = np.zeros(num_dwarfs,dtype=int)
        i = 0
        while i < num_dwarfs:
            r, c = randint(data1_shape[0]), randint(data1_shape[1])
            if not np.isnan(data1[r,c]):
                x0s[i] = c
                y0s[i] = r
                i += 1
    else:
        x0s = np.asarray(positions[0::2],dtype='float')
        y0s = np.asarray(positions[1::2],dtype='float')

    #these are the coordinates of the dwarfs in the new binned image
    xs = np.round(x0s/windowsize).astype(int)
    ys = np.round(y0s/windowsize).astype(int)

    zp, col = getzp(phot_filter)

    #there are other parameters we need to derive using the given parameters, such as b_n, Ieff and Ieff_SB
    b_ns = find_bns(ns,num_dwarfs,verbose)
    Ieffs = find_Ieffs(mags,reffs,ns,b_ns,axisratios,thetas,num_dwarfs,frpath,zp,col,verbose)
    I0s = Ieffs*exp(b_ns)

    Ieff_SBs = 5*log10(res)-2.5*log10(Ieffs)+zp
    I0_SBs = 5*log10(res)-2.5*log10(I0s)+zp

    if psf == 'NO-PSF':
        psfkernel = None
    else:
        with fits.open(psf) as hdul:
            psf_phdu = hdul[0]
            psfkernel = psf_phdu.data

    r999s = find_r999s(b_ns,ns,reffs,num_dwarfs,verbose)

    data_filled, tray_filled = create_convolve_dwarfs(data1,data1_shape,Ieffs,reffs,ns,axisratios,thetas,x0s,y0s,num_dwarfs,r999s,psfkernel,subtract,verbose)
    
    fits.writeto(outdir/f'{signature}_filled.fits',data_filled,header,overwrite=True)
    fits.writeto(outdir/f'{signature}_stickers.fits',tray_filled,header,overwrite=True)

    #if we want reffs in arseconds in the catalog, we convert back using the inverse resolution
    artificial_catalog = np.array((x0s,y0s,mags,Ieff_SBs,I0_SBs,reffs*0.2637,ns,axisratios,thetas,xs,ys)).T
    np.savetxt(outdir/f'{signature}_artificial_dwarfs.catalog',artificial_catalog,fmt=['%-20d','%-20d','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f'],header=f"{'x0':<20s}{'y0':<20s}{'mag':<21s}{'Ieff_SB':<21s}{'I0_SB':<21s}{'reff[pix]':<21s}{'n':<21s}{'axisratio':<21s}{'theta':<21s}{'x':<21s}{'y':<21s}")
    
    if gallery:
        if verbose:
            print("displaying gallery...")
        plot_artificial_gallery(data,outdir,None)

    if verbose:
        print("finished creating artificial image and catalog")

if __name__ == '__main__':
    
    from artificial.create_convolve_dwarfs import create_convolve_dwarfs
    from plot_artificial_gallery import plot_artificial_gallery

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path of the science image containing the real dwarf galaxies. This will be filled with artificial galaxies.')
    parser.add_argument('phot_filter', choices=['u','g','r','i','z'], help='The photometric filter the data was taken in. This is needed to apply the correct zero point magnitude.')
    parser.add_argument('mag_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the apparent magnitude of the artificial dwarfs.')
    parser.add_argument('reff_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the effective radius of the artificial dwarfs, which is the radial distance inside of which half of the light of the dwarf is contained. reff and n are used to calculate the other two Sersic parameters, I0 and bn.')
    parser.add_argument('n_range', nargs=2, type=float, help='Two numbers (low and high) that specify the range of the Sersic index n of the artificial dwarfs. Lower values of n correspond to profiles where the light is more centrally concentrated. reff and n are used to calculate the other two Sersic parameters, I0 and bn.')
    parser.add_argument('axisratio_range', nargs=2, type=float, help='Two numbers (low and high) that specify the axis ratio range of the artificial dwarfs. The axis ratio takes a value from 0 to 1, where 0 is unphysical and 1 is perfectly circular. (It is the complement of the ellipticity)')
    parser.add_argument('theta_range', nargs=2, type=float, help='Two numbers (low and high) that specify the angular offset range of artificial dwarfs, in degrees. Enter 0 and 360 if you want to include all possible angles.')
    parser.add_argument('num_dwarfs', type=int, help='The number of artificial dwarfs to insert into the data image.')
    parser.add_argument('psf', help='Path to the psf used to convolve the artificial dwarfs. If you do not wish to convolve the dwarfs, enter NO-PSF.')
    parser.add_argument('windowsize', type=int, help='The windowsize parameter that will be later used in the detection algorithm. Knowing this allows the program to calculate the coordinates of the artificial dwarfs in the binned image, which is important, since the presence of a detected dwarf at these coordinates indicates a successful detection.')
    parser.add_argument('-reff_units', choices=['as','px','pc'], default='as', help='The units of the previously inputted values for reff_range. Can be arcseconds ("as"), pixels ("px"), or parsecs ("pc"). Default is arcseconds. The program converts between these values using the distance to Centaurus A (3.8E6 pc) and the resolution of DECam (0.2637 "/pix).')
    parser.add_argument('-positions', nargs='*', help='Optional argument that allows you to specify the coordinates of the dwarfs (i.e., positions are non random). List arguments in the format -positions x y x y ...')
    parser.add_argument('-subtract', action='store_true', default=False, help='If toggled, subtracts the created artificial dwarf from the image instead of adding it. Can be useful in testing.')
    parser.add_argument('--gallery', action='store_true', default=False, help='Displays a gallery of images at the end of the artificial dwarf creation procedure. Useful for getting a visual understanding of what happens in the course of the algorithm, and is good for bug-spotting and doing a reality check.')
    parser.add_argument('--signature', help='Optional parameter which allows you to specify the signature, or the name used to identify the output folder and all of its files (if not specified, a name will be created based on the input data image and the current time).')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    phot_filter = args.phot_filter
    mag_range = args.mag_range
    reff_range = args.reff_range
    n_range = args.n_range
    axisratio_range = args.axisratio_range
    theta_range = args.theta_range
    num_dwarfs = args.num_dwarfs
    psf = args.psf
    windowsize = args.windowsize
    reff_units = args.reff_units
    positions = args.positions
    subtract = args.subtract
    gallery = args.gallery
    signature = args.signature
    verbose = args.verbose

    timestr = datetime.now().strftime("-%Y%m%d%H%M%S")
    filenamestr = data.name.split('.')[0]
    if signature is None:
        signature = filenamestr + timestr
    root = Path.cwd().parents[3]
    outdir = Path(root/'OUTPUT'/signature)
    try:
        outdir.mkdir(parents=True)
    except FileExistsError:
        shutil.rmtree(outdir)
        outdir.mkdir(parents=True)
    frpath = Path(root/'PYTHON'/'COMPLETION'/'MATCH_CATALOG'/'ARTIFICIAL'/'DEC_filter_response.txt') 

    with open(outdir/f'{signature}_cmdline_args.txt', 'w') as f:
        json.dump(args.__dict__, f, indent=2)

    get_artificial_catalog(data, phot_filter, mag_range, reff_range, n_range, axisratio_range, theta_range, num_dwarfs, psf, windowsize, reff_units, positions, subtract, gallery, verbose, outdir, frpath, signature)

else:
    from .artificial.create_convolve_dwarfs import create_convolve_dwarfs
    from .plot_artificial_gallery import plot_artificial_gallery
