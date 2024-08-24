import numpy as np
from astropy.modeling.models import Sersic2D
from astropy.io import fits
from numpy import pi, exp
from scipy.special import gamma, gammainc
from scipy.optimize import fsolve
from scipy.signal import fftconvolve
import argparse

def bndefinition(bn,n):
    #This is the REGULARIZED incomplete gamma function, hence the 1 (not gamma(2*n)). See scipy documentation
    return 1 - 2*gammainc(2*n,bn)

def get_bn(n):
    root = fsolve(bndefinition,x0=[1.9992*n-0.3271],args=(n))
    return root[0]

def get_restofterms(reff,n,q):
    bn = get_bn(n)
    return 2*pi*reff**2*n*exp(bn)*bn**(-2*n)*gamma(2*n)*q

def get_flux(mag,zp):
    flux = 10**(-0.4*(mag-zp))
    return flux

def get_Ieff(mag,reff,n,q):
    zp=30
    flux = get_flux(mag,zp)
    restofterms = get_restofterms(reff,n,q)
    Ieff = flux/restofterms
    return Ieff

def insert_dwarf_intoarray(data,psf,mag,reff,n,q,theta,x_off,y_off):

    Ieff = get_Ieff(mag,reff,n,q)
    mod = Sersic2D(amplitude=Ieff, r_eff=reff, n=n, x_0=data.shape[1]/2+x_off, y_0=data.shape[0]/2+y_off, ellip=1-q, theta=np.radians(theta+90))
    x, y = np.meshgrid(np.arange(data.shape[1]), np.arange(data.shape[0]))
    dwarfimg = mod(x, y)

    convolved_dwarf = fftconvolve(dwarfimg,psf,mode='same')

    data += convolved_dwarf

    return data

def insert_dwarf_intofile(data_path,psf_path,mag,reff,n,q,theta,x0,y0,outname):

    with fits.open(data_path) as hdul:
        data = hdul[0].data

    Ieff = get_Ieff(mag,reff,n,q)
    mod = Sersic2D(amplitude=Ieff, r_eff=reff, n=n, x_0=x0, y_0=y0, ellip=1-q, theta=np.radians(theta+90))
    x, y = np.meshgrid(np.arange(data.shape[1]), np.arange(data.shape[0]))
    dwarfimg = mod(x, y)

    with fits.open(psf_path) as hdul:
        psf = hdul[0].data
    psf/=psf.sum()

    convolved_dwarf = fftconvolve(dwarfimg,psf,mode='same')

    data += convolved_dwarf

    fits.writeto(outname,data,overwrite=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_path', help='Filename of the image into which you want to insert the dwarf.')
    parser.add_argument('psf_path', help='Filename of the PSF with which to convolve the dwarf.')
    parser.add_argument('mag', type=float, help='apparent magnitude of the dwarf.')
    parser.add_argument('reff', type=float, help='effective or half-light radius, in pixels, of the dwarf.')
    parser.add_argument('n', type=float, help='sersic index of the dwarf.')
    parser.add_argument('q', type=float, help='axis ratio of the dwarf. Note: axis ratio = 1 - ellipticity. (an axis ratio of 1 describes a radially-symmetric dwarf)')
    parser.add_argument('theta', type=float, help='rotation angle of the dwarf, in degrees.')
    parser.add_argument('x0', type=float,  help='x position of the dwarf, in pixels.')
    parser.add_argument('y0', type=float, help='y position of the dwarf, in pixels.')
    parser.add_argument('outname', help='Output fits file name')

    args = parser.parse_args()
    data_path = args.data_path 
    psf_path = args.psf_path
    mag = args.mag
    reff = args.reff
    n = args.n
    q = args.q
    theta = args.theta
    x0 = args.x0
    y0 = args.y0
    outname = args.outname

    insert_dwarf_intofile(data_path,psf_path,mag,reff,n,q,theta,x0,y0,outname)