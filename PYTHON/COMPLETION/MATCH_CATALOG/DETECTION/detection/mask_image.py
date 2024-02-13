import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
from scipy import ndimage
import argparse
from modest_image import imshow as modest_imshow
import time
import gc

def mask_image(data,outdir,max_dilations,maskfunc,signature,verbose):

    with fits.open(outdir/f'{signature}_segment_objs.fits') as hdul:
        phdu = hdul[0]
        data1 = phdu.data
    segmap = np.asarray(data1,dtype=np.uint16)
    r, c = segmap.shape
    del(data1)
    gc.collect()

    '''if diagnostic_images:
        _, ax = plt.subplots(figsize=(20,20))
        modest_imshow(ax, segmap, interpolation='none', origin='lower', cmap='prism')
        plt.show()'''

    #Mask of True where an object exists
    totalmask = segmap>0
    #1D array of object pixel values
    segmap2 = segmap[totalmask]

    #Highest pixel value in the 1D array
    num_objects = np.amax(segmap2)
    
    #Array of object ids (pixel values of ojects)
    objids = np.arange(1,num_objects+1)
    #A histogram of the object pixels, with the data coming from segmap2 and the bins holding the number of pixels of each value from 1 to the maximum pixel value
    hist, _ = np.histogram(segmap2,bins=np.arange(1,num_objects+2))

    del(segmap2)
    gc.collect()

    '''if diagnostic_images:
        ax = plt.gca()
        modest_imshow(ax, totalmask, interpolation='none', origin='lower')
        plt.show()'''

    #np.argsort puts the indices of the histogram in the order that would cause the histogram to be printed in order of increasing size.
    #We assign the values in this order to the pixel value array and keep the result as a new array.
    #This new array, instead of giving the number of pixels for each object number, gives the object number that it would have
    #if the segmentation map was labelled in order of increasing size.
    size_indices = np.copy(hist)
    size_indices[np.argsort(hist)] = objids

    #Faster computation is possible if the objects in the segmentation map labelled according to increasing size.
    #We iterate through each pixel in the segmentation map and, where not zero, replace it with the correct object number,
    #using the size_indices array computed above.
    if verbose:
        print("converting to size-indexed segmentation map")
    segmap3 = np.zeros((r,c),dtype=np.uint16)
    nonzero_i, nonzero_j = np.nonzero(segmap)
    segmap3[nonzero_i,nonzero_j] = size_indices[segmap[nonzero_i,nonzero_j]-1]

    #An exp(ax^2) function or a sinh(bx) function with parameters selected so that it passes through (1,0) and (num_objects,max_dilations)
    #We supply it with the object ids and obtain an array of floats which can be rounded to yield a suitable number of
    #dilations to perform for each object. (from above, the object ids correspond to the object sizes)
    # UPDATE: we try using a sinh function instead (because smaller objects are masked too much)
    if maskfunc == 'uniform':
        dilations = max_dilations*np.ones(objids.size).astype(int)
    elif maskfunc == 'sqrt':
        a = max_dilations/np.sqrt(num_objects-1)
        dilations = a*np.sqrt(objids-1).astype(int)
    elif maskfunc == 'linear':
        a = max_dilations/(num_objects-1)
        dilations = a*(objids-1).astype(int)
    elif maskfunc == 'pow1.2':
        a = max_dilations/(num_objects-1)**1.2
        dilations = (a*(objids)**1.2).astype(int)
    elif maskfunc == 'exp':
        a = np.log(max_dilations+1)/(num_objects-1)
        expfunc = np.exp(a*(objids-1))-1
        dilations = np.round(expfunc).astype(int)
    elif maskfunc == 'expsq':
        a = np.log(max_dilations+1)/(num_objects-1)**2
        expsqfunc = np.exp(a*(objids-1)**2)-1
        dilations = np.round(expsqfunc).astype(int)
    elif maskfunc == 'sinh':
        num_zeroobjs = int(np.ceil(0.75*num_objects))
        num_sinhobjects = num_objects - num_zeroobjs
        a = np.arcsinh(max_dilations)/num_sinhobjects
        sinhpart = np.round(np.sinh(a*(objids[num_zeroobjs:]-num_zeroobjs))).astype(int)
        dilations = np.concatenate((np.zeros(num_zeroobjs),sinhpart))

    #Now that each object has an associated number of dilations, we wish to find the indices in the dilations array where the changes occur.
    #There will be max_dilation changes. We also include a final index, the last one plus 1, thus making the length of the array max_dilations+1.
    #The 0'th index of this array corresponds to the index in the dilations array where the dilation number changes to 1, and so on.
    dilation_indices = np.zeros(max_dilations+1)
    for i in range(max_dilations):
        dilation_indices[i] = np.argmax(dilations>i)
    dilation_indices[max_dilations] = num_objects

    del(dilations)
    gc.collect()

    diamond = ndimage.generate_binary_structure(2, 1)
    square = ndimage.generate_binary_structure(2, 2)

    #We iterate through the dilation indices, and work with two adjacent indices at a time. The value at dilation_indices[i]
    #corresponds to the index in the dilations array where the dilation number changes from i to i+1. When 1 is added, this
    #also corresponds to the object id (object pixel value) that will experience this increase in dilation number.
    if verbose:
        print("dilating segmentation map")
        t3 = time.perf_counter()
    for i in range(max_dilations):
        if verbose:
            print(i)
        objectsmask = (segmap3>=(dilation_indices[i]+1)) & (segmap3<(dilation_indices[i+1]+1))
        d = i+1
        mask1 = ndimage.binary_dilation(objectsmask, diamond, d)
        mask2 = ndimage.binary_dilation(mask1, square, d)
        totalmask += mask2

    if verbose:
        t4 = time.perf_counter()
        print(f"dilating segmap time: {t4-t3}")
    
    '''if diagnostic_images:
        ax = plt.gca()
        modest_imshow(ax, totalmask, interpolation='none', origin='lower')
        plt.show()'''

    with fits.open(data) as hdul2:
        phdu2 = hdul2[0]
        header2 = phdu2.header
        data2 = phdu2.data

    if verbose:
        t5 = time.perf_counter()
    data2[totalmask] = 0
    if verbose:
        t6 = time.perf_counter()
        print(f"applying mask time: {t6-t5}")

    fits.writeto(outdir/f'{signature}_dilated_mask.fits',totalmask.astype(int),overwrite=True)

    fits.writeto(outdir/f'{signature}_masked.fits',data2,header2,overwrite=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Filename of the original image.')
    parser.add_argument('segmap', help='Filename of the segmentation image.')
    parser.add_argument('max_dilations', type=int, help='Number of iterations for the mask booster.')
    parser.add_argument('verbose', default=False, help='Displays images and messages')
    parser.add_argument('save', default=False, help='Whether or not to save the image.')

    args = parser.parse_args()
    filename = args.data
    segmap = args.segmap
    max_dilations = args.max_dilations
    verbose = args.verbose
    save = args.save

    mask_image(filename,segmap,max_dilations,verbose,save)