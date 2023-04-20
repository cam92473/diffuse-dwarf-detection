from astropy.io import fits
from matplotlib import pyplot as plt
import numpy as np
import argparse
from astropy.stats import sigma_clip
from scipy.odr import Data, Model, ODR
from math import hypot
from scipy.optimize import fsolve

def exponential(B,x):
    return B[0]*np.exp(B[1]*x)+B[2]

def closest_x_on_exp(x,x_p,y_p,A,a,b):
    return (A*np.exp(a*x)+b-y_p)*(A*a*np.exp(a*x))+(x-x_p)

def filter_table(filename,sig_beneath,sig_right,verify,wheresave):
    hdul = fits.open(filename)
    hdue = hdul[2]
    header = hdue.header
    data = hdue.data

    if verify:
        print("filtering table")

    m_mask = data['MAG_AUTO']!=99.
    data = data[m_mask]
    f_mask = data['FLUX_RADIUS']>=0
    data = data[f_mask]
    num_bad = (~m_mask).sum() + (~f_mask).sum()
    if verify:
        print("{} initial detections".format(data.size))
        print("{} bad detections removed".format(num_bad))

    data = data[np.argsort(data['FLUX_RADIUS'])]
    f = data['FLUX_RADIUS']
    m = data['MAG_AUTO']

    expon = Model(exponential)
    mydata = Data(f,m)
    myodr = ODR(mydata, expon, beta0=[4., -0.2, -6.5])
    myoutput = myodr.run()
    B = myoutput.beta
    fitted = exponential(B,f)

    num_points = data.size
    dists = np.zeros(num_points)
    guess = 0.5
    for p in range(num_points):
        f_p = f[p]
        m_p = m[p]
        f_e = fsolve(closest_x_on_exp,guess,args=(f_p,m_p,B[0],B[1],B[2]))
        m_e = exponential(B,f_e)
        dist = hypot(f_e-f_p,m_e-m_p)
        if m_e > m_p:
            dist *= -1
        dists[p] = dist

    clipped = sigma_clip(dists,sigma_lower=sig_beneath,sigma_upper=100,cenfunc='mean')
    data2 = data[clipped.mask]
    f2 = data2['FLUX_RADIUS']
    m2 = data2['MAG_AUTO']

    '''clipped = sigma_clip(f2,sigma_lower=100,sigma_upper=sig_right,cenfunc='mean')
    data3 = data2[clipped.mask]
    f3 = data3['FLUX_RADIUS']
    m3 = data3['MAG_AUTO']'''

    if verify:
        print("number of candidates: ",data2.size)
        '''_, ax = plt.subplots(figsize=(20,20))
        ax.scatter(f,m,c='r')
        ax.plot(f,fitted,c='b')
        if data2.size != 0:
            ax.scatter(f2,m2,c='g')
        plt.show()'''

    if wheresave is not None:
        fits.writeto(wheresave,data2,header,overwrite=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('filename', help='Filename of the original image.')
    parser.add_argument('sigclip', help='Filename of the original image.')
    parser.add_argument('verify', help='Filename of the original image.')
    parser.add_argument('wheresave', help='Filename of the original image.')

    args = parser.parse_args()
    filename = args.filename
    sigclip = args.sigclip
    verify = args.verify
    wheresave = args.wheresave

    filter_table(filename,sigclip,verify,wheresave)