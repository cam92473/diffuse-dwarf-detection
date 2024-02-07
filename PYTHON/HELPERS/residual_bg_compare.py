import numpy as np
import argparse
from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

def compare(image, aperture_resid, aperture_bg, size):
    with fits.open(image) as hdul:
        phdu = hdul[0]
        data = phdu.data
        shape = phdu.shape

    Y1, X1 = aperture_resid[0], aperture_resid[1] 
    Y2, X2 = aperture_bg[0], aperture_bg[1] 
    xx, yy = np.mgrid[:shape[0],:shape[1]]

    coor = (xx-X1)**2+(yy-Y1)**2
    coob = (xx-X2)**2+(yy-Y2)**2

    pos_data = data - data.min() + 1

    plt.imshow(pos_data, norm=LogNorm(vmin=30,vmax=50), origin='lower')
    plt.imshow(coor<size**2, origin='lower', alpha=(coor<size**2)*0.5)
    plt.title("residual aperture")
    plt.show()

    plt.imshow(pos_data, norm=LogNorm(vmin=30,vmax=50), origin='lower')
    plt.imshow(coob<size**2, origin='lower', alpha=(coob<size**2)*0.5)
    plt.title("background aperture")
    plt.show()

    aperture_r = data[coor<=size**2]
    aperture_b = data[coob<=size**2]

    mean_r = np.mean(aperture_r)
    std_r = np.std(aperture_r)
    mean_b = np.mean(aperture_b)
    std_b = np.std(aperture_b)

    print(f"mean of residual: {mean_r}")
    print(f"std of residual: {std_r}")
    print(f"mean of background: {mean_b}")
    print(f"std of background: {std_b}")

    perc_diff_mean = np.abs(mean_r-mean_b)/((mean_r+mean_b)/2)*100 
    print(f"percent difference between means: {perc_diff_mean}")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('image', help='')
    parser.add_argument('aperture_resid', nargs=2, type=int, help='')
    parser.add_argument('aperture_bg', nargs=2, type=int, help='')
    parser.add_argument('size', type=int, help='Radius of the aperture used for both the residual and the background.')

    args = parser.parse_args()

    compare(args.image, args.aperture_resid, args.aperture_bg, args.size)