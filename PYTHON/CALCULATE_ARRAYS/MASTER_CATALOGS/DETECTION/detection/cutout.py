from astropy.io import fits
from astropy.wcs import WCS
import argparse
import pandas as pd
import time
import numpy as np
import PIL.Image
import skimage as ski

def attach_zero(num):
    if len(num) == 1:
        num = '0'+num
    return num

def get_bounds(arr):
    hist = np.histogram(arr,bins=1000)
    left_ind = np.argmax(hist[0])
    mode = hist[1][left_ind]
    vmin = mode
    vmax = np.nanpercentile(arr,98)
    return vmin, vmax

def save_cutouts(rgb_image,suffix,X,Y,data_wcs,rgb_wcs,output_root):
    rgb = ski.io.imread(rgb_image)
    for i in range(len(X)):
        skyc = data_wcs.pixel_to_world(X[i],Y[i])
        rgbpix = rgb_wcs.world_to_pixel(skyc)
        cutout = rgb[(rgb.shape[0]-int(rgbpix[1])-200):(rgb.shape[0]-int(rgbpix[1])+200),(int(rgbpix[0])-200):(int(rgbpix[0])+200)]

        rah, ram, ras = skyc.ra.hms
        ddg, dam, das = skyc.dec.dms
        rah = str(int(rah))
        ram = attach_zero(str(int(ram)))
        ras = attach_zero(str(round(ras)))
        ddg = str(abs(int(ddg)))
        dam = attach_zero(str(abs(int(dam))))
        das = attach_zero(str(abs(round(das))))
        name = f'dc{rah}{ram}{ras}_{ddg}{dam}{das}_{suffix}.jpg'

        ski.io.imsave(str(output_root/'cutouts'/name),cutout)

def make_cutouts(output_root, phot_filters, rgb_dir, signature, verbose):

    t1 = time.perf_counter()

    (output_root/'cutouts').mkdir(parents=True,exist_ok=True)

    filt_det = pd.read_csv(output_root/'csv'/f'{signature}_filtered_detections.csv')
    X = filt_det['X_IMAGE']
    Y = filt_det['Y_IMAGE']

    with fits.open(output_root/phot_filters[0]/f'{signature}_1a_data_{phot_filters[0]}.fits') as hdul:
        data_header = hdul[0].header
    data_wcs = WCS(data_header)

    with fits.open(rgb_dir/'tile4cut_i.fits') as hdul:
        rgb_header = hdul[0].header
    rgb_wcs = WCS(rgb_header)

    rgb_images = [str(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_shadowsadjust.tif'),str(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_autoequalize.tif'),str(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_posterize.tif')]
    suffixes = ['1sa','2ae','3p']

    PIL.Image.MAX_IMAGE_PIXELS = np.inf
    for i in range(len(rgb_images)):
        rgb_image = rgb_images[i]
        suffix = suffixes[i]
        save_cutouts(rgb_image,suffix,X,Y,data_wcs,rgb_wcs,output_root)

    t2 = time.perf_counter()

    if verbose:
        print(f'making cutouts: {t2-t1}')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Cut out a region from a larger image and save it as its own fits image.')
    parser.add_argument('filename', help='The filename of the input image containing the dwarfs.')
    parser.add_argument('location', help='The location of the dwarf. Supply either the ICRS sexagesimal coordinates of the dwarf, given as "[-]##h##m##.##s [-]##d##m##.##s", or a pixel coordinate, given as "#### ####". Be sure to include the quotations around the argument so that argparse interprets the input as a single argument.')
    parser.add_argument('width', type=int, help='The width of the cutout in pixels')
    parser.add_argument('height', type=int, help='The height of the cutout in pixels')
    parser.add_argument('dwarfname', help='The name of the dwarf that can be used as the output fits filename.')
    args = parser.parse_args()

    dwarf_cutout(args.filename, args.location, args.width, args.height, args.dwarfname)



    '''
    
    LEGACY CODE
    
    rgb = pyvips.Image.new_from_file(str(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_posterize.jpg'))
    for i in range(len(X)):
        skyc = data_wcs.pixel_to_world(X[i],Y[i])
        rgbpix = rgb_wcs.world_to_pixel(skyc)
        #rgbpix[0]-200,rgb_sa.height-rgbpix[1]-200,rgbpix[0]+200,rgb_sa.height-rgbpix[1]+200
        cutout = rgb.crop(rgbpix[0]-200,rgb.height-rgbpix[1]-200,400,400)
        #cutout = Cutout2D(data, position=(X[i],Y[i]), size=(800,800))
        #vmin, vmax = get_bounds(cutout.data)
        
        rah, ram, ras = skyc.ra.hms
        ddg, dam, das = skyc.dec.dms
        rah = str(int(rah))
        ram = attach_zero(str(int(ram)))
        ras = attach_zero(str(round(ras)))
        ddg = str(abs(int(ddg)))
        dam = attach_zero(str(abs(int(dam))))
        das = attach_zero(str(abs(round(das))))
        name = f'dc{rah}{ram}{ras}_{ddg}{dam}{das}.jpg'

        cutout.write_to_file(str(output_root/'cutouts'/name))'''

    '''PIL.Image.MAX_IMAGE_PIXELS = np.inf
    #rgb_image = PIL.Image.open(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1.jpg')
    with PIL.Image.open(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_shadows_adjust.jpg') as rgb_sa:
        rgb_dims = rgb_sa.size
        for i in range(len(X)):
            skyc = data_wcs.pixel_to_world(X[i],Y[i])
            rgbpix = rgb_wcs.world_to_pixel(skyc)
            cutout_dims = (rgbpix[0]-200,rgb_dims[1]-rgbpix[1]-200,rgbpix[0]+200,rgb_dims[1]-rgbpix[1]+200)
            cutout_sa = rgb_sa.crop(cutout_dims)
            #cutout = Cutout2D(data, position=(X[i],Y[i]), size=(800,800))
            #vmin, vmax = get_bounds(cutout.data)
            
            rah, ram, ras = skyc.ra.hms
            ddg, dam, das = skyc.dec.dms
            rah = str(int(rah))
            ram = attach_zero(str(int(ram)))
            ras = attach_zero(str(round(ras)))
            ddg = str(abs(int(ddg)))
            dam = attach_zero(str(abs(int(dam))))
            das = attach_zero(str(abs(round(das))))
            name_sa = f'dc{rah}{ram}{ras}_{ddg}{dam}{das}_1sa.jpg'

            cutout_sa.save(output_root/'cutouts'/name_sa)

    del(rgb_sa)
    gc.collect()'''

    '''with PIL.Image.open(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_autoequalize.jpg') as rgb_ae:
        rgb_dims = rgb_ae.size
        for i in range(len(X)):
            skyc = data_wcs.pixel_to_world(X[i],Y[i])
            rgbpix = rgb_wcs.world_to_pixel(skyc)
            cutout_dims = (rgbpix[0]-200,rgb_dims[1]-rgbpix[1]-200,rgbpix[0]+200,rgb_dims[1]-rgbpix[1]+200)
            cutout_ae = rgb_ae.crop(cutout_dims)
            #cutout = Cutout2D(data, position=(X[i],Y[i]), size=(800,800))
            #vmin, vmax = get_bounds(cutout.data)
            
            rah, ram, ras = skyc.ra.hms
            ddg, dam, das = skyc.dec.dms
            rah = str(int(rah))
            ram = attach_zero(str(int(ram)))
            ras = attach_zero(str(round(ras)))
            ddg = str(abs(int(ddg)))
            dam = attach_zero(str(abs(int(dam))))
            das = attach_zero(str(abs(round(das))))
            name_ae = f'dc{rah}{ram}{ras}_{ddg}{dam}{das}_2ae.jpg'

            cutout_ae.save(output_root/'cutouts'/name_ae)
    
    del(rgb_ae)
    gc.collect()

    with PIL.Image.open(rgb_dir/'scabs_TILE4_FILTERSzgu_asinh_v1_posterize.jpg') as rgb_p:
        rgb_dims = rgb_p.size
        for i in range(len(X)):
            skyc = data_wcs.pixel_to_world(X[i],Y[i])
            rgbpix = rgb_wcs.world_to_pixel(skyc)
            cutout_dims = (rgbpix[0]-200,rgb_dims[1]-rgbpix[1]-200,rgbpix[0]+200,rgb_dims[1]-rgbpix[1]+200)
            cutout_p = rgb_p.crop(cutout_dims)
            #cutout = Cutout2D(data, position=(X[i],Y[i]), size=(800,800))
            #vmin, vmax = get_bounds(cutout.data)
            
            rah, ram, ras = skyc.ra.hms
            ddg, dam, das = skyc.dec.dms
            rah = str(int(rah))
            ram = attach_zero(str(int(ram)))
            ras = attach_zero(str(round(ras)))
            ddg = str(abs(int(ddg)))
            dam = attach_zero(str(abs(int(dam))))
            das = attach_zero(str(abs(round(das))))
            name_p = f'dc{rah}{ram}{ras}_{ddg}{dam}{das}_3p.jpg'

            cutout_p.save(output_root/'cutouts'/name_p)'''
