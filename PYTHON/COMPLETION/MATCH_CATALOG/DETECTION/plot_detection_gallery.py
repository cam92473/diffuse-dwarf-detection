import argparse
from pathlib import Path
from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, BoundaryNorm
import numpy as np

def plot_secondgroup(imgarr,savename,artificial):
    fig, axl = plt.subplots(2,3,figsize=(20,10),layout='compressed')
    axl[0,1].imshow(imgarr[4],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
    axl[0,1].set_title('masked image')
    axl[0,1].get_xaxis().set_visible(False)
    axl[0,1].get_yaxis().set_visible(False)
    axl[0,2].imshow(imgarr[5],cmap='cividis',origin='lower',norm=LogNorm())
    axl[0,2].set_title('binned image')
    axl[0,2].get_xaxis().set_visible(False)
    axl[0,2].get_yaxis().set_visible(False)
    axl[1,0].imshow(imgarr[5],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[5].mean()-0.2*imgarr[5].std(),vmax=imgarr[5].mean()+0.5*imgarr[5].std(),clip=True))
    axl[1,0].set_title('binned image, rescaled',y=-0.07)
    axl[1,0].get_xaxis().set_visible(False)
    axl[1,0].get_yaxis().set_visible(False)
    axl[1,1].imshow(imgarr[6],cmap='cividis',origin='lower',norm=BoundaryNorm([0,1,imgarr[5].max()],256))
    axl[1,1].set_title('segmented detections',y=-0.07)
    axl[1,1].get_xaxis().set_visible(False)
    axl[1,1].get_yaxis().set_visible(False)
    #axl[1,2].imshow(imgarr[7],cmap='cividis',origin='lower',norm=BoundaryNorm([0,1,imgarr[0].max()],256))
    axl[1,2].set_title('filtered detections',y=-0.07)
    axl[1,2].get_xaxis().set_visible(False)
    axl[1,2].get_yaxis().set_visible(False)

    if artificial:
        axl[0,0].imshow(imgarr[1],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
        axl[0,0].set_title('artificial dwarfs only')
        axl[0,0].get_xaxis().set_visible(False)
        axl[0,0].get_yaxis().set_visible(False)
    else:
        axl[0,0].remove()

    if savename is not None:
        savename2 = savename.name.split('.')[0]+'_binning_and_filtering.png'
        plt.savefig(savename.parents/savename2)
    
    plt.show()

def plot_firstgroup(imgarr,savename,artificial):
    fig, axl = plt.subplots(2,3,figsize=(20,10),layout='compressed')
    axl[0,1].imshow(imgarr[0],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
    axl[0,1].set_title('original image')
    axl[0,1].get_xaxis().set_visible(False)
    axl[0,1].get_yaxis().set_visible(False)
    axl[0,2].imshow(imgarr[2],cmap='cividis',origin='lower',norm=BoundaryNorm([0,1,imgarr[2].max()],256))
    axl[0,2].set_title('segmented objects')
    axl[0,2].get_xaxis().set_visible(False)
    axl[0,2].get_yaxis().set_visible(False)
    axl[1,0].imshow(imgarr[3],cmap='cividis',origin='lower',norm=BoundaryNorm([0,1,imgarr[3].max()],256))
    axl[1,0].set_title('dilated mask',y=-0.07)
    axl[1,0].get_xaxis().set_visible(False)
    axl[1,0].get_yaxis().set_visible(False)
    axl[1,1].imshow(imgarr[4],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
    axl[1,1].set_title('masked image',y=-0.07)
    axl[1,1].get_xaxis().set_visible(False)
    axl[1,1].get_yaxis().set_visible(False)
    axl[1,2].imshow(imgarr[5],cmap='cividis',origin='lower',norm=LogNorm())
    axl[1,2].set_title('binned image',y=-0.07)
    axl[1,2].get_xaxis().set_visible(False)
    axl[1,2].get_yaxis().set_visible(False)

    if artificial:
        axl[0,0].imshow(imgarr[1],cmap='cividis',origin='lower',norm=LogNorm(vmin=imgarr[0].mean()-0.2*imgarr[0].std(),vmax=imgarr[0].mean()+0.5*imgarr[0].std(),clip=True))
        axl[0,0].set_title('artificial dwarfs')
        axl[0,0].get_xaxis().set_visible(False)
        axl[0,0].get_yaxis().set_visible(False)
        axl[0,1].set_title('original image with artificial dwarfs')
    else:
        axl[0,0].remove()

    if savename is not None:
        savename1 = savename.name.split('.')[0]+'_masking_and_binning.png'
        plt.savefig(savename.parents/savename1)
    
    plt.show()

def plot_detection_gallery(data,outdir,savename):

    artificial = data.name.split('.')[0][-6:]=='filled'

    imgarr = np.zeros(8,dtype=object)
    #images will be filled in the following order: data, artificial only, objs, dilated mask, masked, binned, dets, filtered
    with fits.open(data) as hdul:
        imgarr[0] = hdul[0].data
    for f in outdir.glob('*.fits'):
        with fits.open(f) as hdul:
            if f.name.split('.')[0][-8:] == 'stickers':
                imgarr[1] = hdul[0].data
            if f.name.split('.')[0][-12:] == 'segment_objs':
                imgarr[2] = hdul[0].data
            if f.name.split('.')[0][-12:] == 'dilated_mask':
                imgarr[3] = hdul[0].data
            if f.name.split('.')[0][-6:] == 'masked':
                imgarr[4] = hdul[0].data
            if f.name.split('.')[0][-6:] == 'binned':
                imgarr[5] = hdul[0].data
            if f.name.split('.')[0][-12:] == 'segment_dets':
                imgarr[6] = hdul[0].data
            if f.name.split('.')[0][-8:] == 'filtered':
                imgarr[7] = hdul[0].data

    #transpose certain images into the region >+1 to be able to render them on a log scale
    imgarr[0] = imgarr[0]-imgarr[0].min()+1
    if artificial:
        imgarr[1] = imgarr[1]-imgarr[1].min()+1
    imgarr[4] = imgarr[4]-imgarr[4].min()+1
    imgarr[5] = imgarr[5]-imgarr[5].min()+1
    #imgarr[7] = imgarr[7]-imgarr[7].min()+1

    plot_firstgroup(imgarr,savename,artificial)
    plot_secondgroup(imgarr,savename,artificial)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Path to the image input into the detection algorithm.')
    parser.add_argument('outdir', help='Path to the output folder containing the images you want to plot.')
    parser.add_argument('-savename', help='Specify a new file name if you want to save the replotted image.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    outdir = Path(args.outdir).resolve()
    savename = args.savename

    plot_detection_gallery(data,outdir,savename)