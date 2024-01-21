import argparse
from binning import binning
from pathlib import Path
import numpy as np
from astropy.io import fits

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('dwarf', help='dwarf')
    parser.add_argument('seg', help='seg')
    parser.add_argument('windowsize', default=10, type=int, help='Size of the window used to bin the pixels in the masked image. The image is divided into square windows having the specified sidelength. The median of the pixels within each window is written to a single pixel in the output image.')

    args = parser.parse_args()
    dwarf = args.dwarf
    dwarfname = (dwarf.split('/')[1])[:-5]
    seg = args.seg
    windowsize = args.windowsize
    verify = True

    cwd = Path.cwd()
    dwarfs_dir = cwd/'individual_dwarfs'
    masked_dir = cwd/'masked_dwarfs'
    binned_dir = cwd/'binned_dwarfs'

    hdul1 = fits.open(seg)
    phdu1 = hdul1[0]
    data1 = phdu1.data
    segmap = np.asarray(data1,dtype=int)
    mask = segmap==0
    hdul2 = fits.open(dwarf)
    phdu2 = hdul2[0]
    data2 = phdu2.data
    header2 = phdu2.header
    masked = data2 * mask
    fits.writeto(masked_dir/(dwarfname+'_masked.fits'),masked,header2,overwrite=True)

    binning(masked_dir/(dwarfname+'_masked.fits'), windowsize, verify, binned_dir/(dwarfname+'_binned.fits'))


