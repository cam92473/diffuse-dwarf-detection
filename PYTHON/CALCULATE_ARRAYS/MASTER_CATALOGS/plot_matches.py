import matplotlib.pyplot as plt
import numpy as np
import argparse
import pandas as pd
from matplotlib.colors import LogNorm
from pathlib import Path
from astropy.io import fits
from astropy.nddata import Cutout2D
from matplotlib.patches import Rectangle, Circle
from astropy.visualization import LogStretch, ImageNormalize

def plot_matches(outdir,signature,windowsize,verbose):

    #header = [' x0','y0','gmag','Ieff_SB','I0_SB','reff','n','axisratio','theta','x','y']
    matchcat = pd.read_csv(outdir/f'{signature}_matches.catalog', sep='\s+', escapechar='#').to_numpy()
    nonmatchcat = pd.read_csv(outdir/f'{signature}_nonmatches.catalog', sep='\s+', escapechar='#').to_numpy()
    #detcat = pd.read_csv(outdir/f'{signature}_filtered_detections.catalog', sep='\s+', escapechar='#').to_numpy()

    circs = []
    rects = []
    for row in matchcat:
        circs.append(Circle((row[0],row[1]),100,edgecolor='r',fill=False))
    for row in nonmatchcat:
        rects.append(Rectangle((row[6]*windowsize,row[7]*windowsize),100,100,edgecolor='g',fill=False))

    with fits.open(outdir/f'{signature}_filled.fits') as hdul:
        data = hdul[0].data
    data = data-data.min()+1

    fig, axs = plt.subplots(1,3,figsize=(20,10))

    p1 = 1.0
    p2 = 99.0
    vmin = np.percentile(data.ravel(),p1)
    vmax = np.percentile(data.ravel(),p2)

    norm = ImageNormalize(data,vmin=vmin, vmax=vmax, stretch=LogStretch())

    axs[0].imshow(data,cmap='cividis',origin='lower',norm=norm)
    axs[0].set_title('original image with artificial dwarfs')
    axs[1].imshow(data,cmap='cividis',origin='lower',norm=norm)
    axs[1].set_title('matches')
    axs[2].imshow(data,cmap='cividis',origin='lower',norm=norm)
    axs[2].set_title('non-matches')

    '''axs[0].imshow(data,cmap='cividis',origin='lower',norm=LogNorm(vmin=data.mean()-0.2*data.std(),vmax=data.mean()+0.5*data.std(),clip=True))
    axs[0].set_title('original image with artificial dwarfs')
    axs[1].imshow(data,cmap='cividis',origin='lower',norm=LogNorm(vmin=data.mean()-0.2*data.std(),vmax=data.mean()+0.5*data.std(),clip=True))
    axs[1].set_title('matches')'''
    for circle in circs:
        axs[1].add_patch(circle)
    '''axs[2].imshow(data,cmap='cividis',origin='lower',norm=LogNorm(vmin=data.mean()-0.2*data.std(),vmax=data.mean()+0.5*data.std(),clip=True))
    axs[2].set_title('non-matches')'''
    for rectangle in rects:
        axs[2].add_patch(rectangle)

    plt.show()    


    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')

    #parser.add_argument('original_im', help='Original image.')
    parser.add_argument('outdir', help='Output folder containing the match and nonmatch catalogs of a single run.')
    parser.add_argument('signature', help='The signature used to identify the files in the output folder.')
    parser.add_argument('windowsize', type=int, help='')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    #original_im = Path(args.original_im).resolve()
    outdir = Path(args.outdir).resolve()
    windowsize = args.windowsize
    signature = args.signature
    verbose = args.verbose

    plot_matches(outdir,signature,windowsize,verbose)