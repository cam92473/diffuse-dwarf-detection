import argparse
from pathlib import Path
from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

def plot_artificial_gallery(original_im,art_folder,savename):

    imgarr = np.zeros(3,dtype=object)
    #images will be filled in the following order: original, objs, dilated mask, masked, binned, dets, filtered
    with fits.open(original_im) as hdul:
        imgarr[0] = hdul[0].data
    for f in art_folder.glob('*.fits'):
        with fits.open(f) as hdul:
            if f.name.split('.')[-2][-8:] == 'stickers':
                imgarr[1] = hdul[0].data
            if f.name.split('.')[-2][-6:] == 'filled':
                imgarr[2] = hdul[0].data

    #transpose certain images into the region >+1 to be able to render them on a log scale
    imgarr[0] = imgarr[0]-imgarr[0].min()+1
    imgarr[1] = imgarr[1]-imgarr[1].min()+1
    imgarr[2] = imgarr[2]-imgarr[2].min()+1

    fig, axl = plt.subplots(1,3,figsize=(20,10))
    axl[0].imshow(imgarr[0],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
    axl[0].set_title('original image')
    axl[1].imshow(imgarr[1],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
    axl[1].set_title('artificial dwarfs')
    axl[2].imshow(imgarr[2],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
    axl[2].set_title('original image with artificial dwarfs')

    plt.tight_layout()

    if savename is not None:
        plt.savefig(savename)

    plt.show()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('original_im', help='Path to the original data image input into the artificial dwarf algorithm.')
    parser.add_argument('art_folder', help='Path to the folder containing the artificial dwarf images you want to plot.')
    parser.add_argument('-savename', help='Specify a new file name if you want to save the replotted image.')

    args = parser.parse_args()
    original_im = Path(args.original_im).resolve()
    art_folder = Path(args.art_folder).resolve()
    savename = args.savename

    plot_artificial_gallery(original_im,art_folder,savename)