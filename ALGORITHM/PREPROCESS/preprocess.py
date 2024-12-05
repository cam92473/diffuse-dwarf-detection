import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clip
import argparse
import shutil
import warnings

def clip(data):
    warnings.filterwarnings("ignore", category=UserWarning, module="astropy.stats.sigma_clipping")
    clipped = sigma_clip(data,sigma_lower=5,sigma_upper=15)
    median = np.nanmedian(data)
    hi_mask = clipped.mask & (data>median)
    lo_mask = clipped.mask & (data<median)
    data[hi_mask] = np.nanmax(data[~clipped.mask])
    data[lo_mask] = np.nanmin(data[~clipped.mask])
    return data

def gimp_ready(data):
    data[np.isnan(data)] = np.nanmin(data)
    data = np.pad(data,1,mode='constant',constant_values=np.nan)
    return data

def preprocess(data_in_file,weight_in_file,data_out_file,weight_out_file,name="",verbosity=1):

    if verbosity > 0:
        print(f"  preprocessing{name}...")

    with fits.open(data_in_file) as hdul:
        data = hdul[0].data
        hdr = hdul[0].header
    
    data = clip(data)
    data = gimp_ready(data)

    fits.writeto(data_out_file,data,hdr,overwrite=True)
    shutil.move(weight_in_file,weight_out_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_in_file', help='Input data file to be preprocessed.')
    parser.add_argument('weight_in_file', help='Associated weight image.')
    parser.add_argument('data_out_file', help='Where to write the preprocessed data file to.')
    parser.add_argument('weight_out_file', help='Where to move the weight file to (since preprocessing has no effect on the weight).')

    args = parser.parse_args()

    preprocess(args.data_in_file,args.weight_in_file,args.data_out_file,args.weight_out_file)
