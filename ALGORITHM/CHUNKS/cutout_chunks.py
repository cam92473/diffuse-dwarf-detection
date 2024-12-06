from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import Cutout2D
import argparse
import colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime

def create_signature(data_in_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{data_in_file.stem}_{timestr}"
    return signature

def cutout_chunks(data_in_file,weight_in_file,data_out_folder,weight_out_folder,jpeg_in_file,jpeg_out_file,save=False,signature=None,verbosity=1):

    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Chunking...")

    signature = create_signature(data_in_file,signature)

    with fits.open(data_in_file) as hdul:
        header = hdul[0].header
        data = hdul[0].data
    with fits.open(weight_in_file) as hdul:
        weight = hdul[0].data
    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']
        
    x = [10160,15697,21210,5040,10369,15697,21017,26336,3806,8565,13324,18083,22842,27600,3806,8565,13324,18083,22842,27600,5040,10369,15697,21017,26336,10160,15697,21210]
    y = [25390,25390,25390,20850,20850,20850,20850,20850,16652,16280,16280,16280,16280,16280,12280,12280,12280,12280,12280,12280,7697,7697,7697,7697,7697,3192,3192,3192]
    color_coords = [round(t[i] * 255) for t in [colorsys.hsv_to_rgb(h, 1, 1) for h in [i/28 for i in list(range(0,28))]] for i in range(3)]
    colors = list(zip(color_coords[::3],color_coords[1::3],color_coords[2::3]))

    if save:
        if verbosity > 0:
            print("  making chunks diagram...")
        Image.MAX_IMAGE_PIXELS = np.inf
        im = Image.open(jpeg_in_file)
        im_r = im.resize((im.width // 2, im.height // 2))
        draw = ImageDraw.Draw(im_r)
        for i in range(28):
            draw.rectangle(((x[i]-3000)/2,im_r.height-(y[i]-2500)/2,(x[i]+3000)/2,im_r.height-(y[i]+2500)/2),outline=colors[i],width=30)
            draw.text((x[i]/2, im_r.height-y[i]/2), str(i+1), fill=colors[i], font=ImageFont.truetype("Ubuntu-R.ttf", 600))
        im_r.save(jpeg_out_file,"JPEG",quality=85,optimize=True)

    for i in range(1):
        chunk = f"chunk{i+1}"
        if verbosity > 0:
            print(f"  cutting out {chunk}...")


        data_cutout = data
        weight_cutout = weight

        '''data_cutout = Cutout2D(data, position=(x[i],y[i]), size=(5000,6000), wcs=wcs, mode='strict')
        weight_cutout = Cutout2D(weight, position=(x[i],y[i]), size=(5000,6000), wcs=wcs, mode='strict')

        header.update(data_cutout.wcs.to_header())'''

        #data_cutout.data
        #weight_cutout.data

        fits.writeto(data_out_folder/f'{signature}_{chunk}.fits', data_cutout, header, overwrite=True)
        fits.writeto(weight_out_folder/f'{signature}_{chunk}_weight.fits', weight_cutout, header, overwrite=True)

    t2 = time.perf_counter()

    if verbosity > 0:
        print(f" Finished chunking. Total time: {t2-t1}")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Divides tile into 28 chunks (both data and weight).')
    parser.add_argument('data_in_file', help='Input data tile')
    parser.add_argument('weight_in_file', help='Input weight tile')
    parser.add_argument('data_out_folder', help='Output folder for data chunks')
    parser.add_argument('weight_out_folder', help='Output folder for weight chunks')
    parser.add_argument('-jpeg_in_file', help='The filename of the input jpeg (for save=True).')
    parser.add_argument('-jpeg_out_file', help='The filename of the output jpeg (for save=True).')
    parser.add_argument('--save', action='store_true', default=False, help='Saves a diagram showing the chunks overlaid on the jpeg specified in "jpeg_in_file".')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', default=1, choices=[0,1,2], help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    
    cutout_chunks(args.data_in_file,args.weight_in_file,args.data_out_folder,args.weight_out_folder,args.jpeg_in_file,args.jpeg_out_file,save=args.save,signature=args.signature,verbosity=args.verbosity)