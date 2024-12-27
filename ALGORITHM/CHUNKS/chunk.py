from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata import Cutout2D
import argparse
import colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import json
from PIL import Image, ImageTk
import tkinter as tk
import warnings
from astropy.stats import sigma_clip

def fits_to_pil(data):
    warnings.filterwarnings("ignore", category=UserWarning, module="astropy.stats.sigma_clipping")
    data_copy = np.copy(data)
    clipped = sigma_clip(data_copy,sigma=3)
    median = np.nanmedian(data_copy)
    hi_mask = clipped.mask & (data_copy>median)
    lo_mask = clipped.mask & (data_copy<median)
    data_copy[hi_mask] = np.nanmax(data_copy[~clipped.mask])
    data_copy[lo_mask] = np.nanmin(data_copy[~clipped.mask])
    data_copy -= np.nanmin(data_copy)
    data_copy *= 255/np.nanmax(data_copy)
    data_copy = np.flipud(data_copy)
    image = Image.fromarray(data_copy)
    image = image.convert('RGB')

    return image

def tk_display(final_composite,title):
    root = tk.Tk()
    root.title(title)
    final_composite.thumbnail((800, 800))
    photo = ImageTk.PhotoImage(final_composite)
    width, height = final_composite.size
    root.geometry(f"{width}x{height}")
    label = tk.Label(root, image=photo)
    label.pack()
    root.after(3000, root.destroy)
    root.mainloop()

def create_signature(data_in_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{data_in_file.stem}_{timestr}"
    return signature

def chunk(data_in_file,data_out_folder,is_tile,chunkinfo_json,tile_color_jpeg,save_dir,save=False,play_through=False,signature=None,verbosity=1):

    signature = create_signature(data_in_file,signature)

    with fits.open(data_in_file) as hdul:
        header = hdul[0].header
        data = hdul[0].data
    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']

    with open(chunkinfo_json,'r') as f:
        info = json.load(f)
    x, y = info['x'], info['y']
    chunk_width, chunk_height = info['width'], info['height']

    num_chunks = len(x)
    #x = [10160,15697,21210,5040,10369,15697,21017,26336,3806,8565,13324,18083,22842,27600,3806,8565,13324,18083,22842,27600,5040,10369,15697,21017,26336,10160,15697,21210]
    #y = [25390,25390,25390,20850,20850,20850,20850,20850,16652,16280,16280,16280,16280,16280,12280,12280,12280,12280,12280,12280,7697,7697,7697,7697,7697,3192,3192,3192]
    color_coords = [round(t[i] * 255) for t in [colorsys.hsv_to_rgb(h, 1, 1) for h in [i/num_chunks for i in list(range(0,num_chunks))]] for i in range(3)]
    colors = list(zip(color_coords[::3],color_coords[1::3],color_coords[2::3]))

    if (save | play_through):
        if verbosity > 0:
            print("  making chunks diagram...")
        if is_tile:
            Image.MAX_IMAGE_PIXELS = np.inf
            image = Image.open(tile_color_jpeg)
            image = image.resize((image.width // 2, image.height // 2))
            draw = ImageDraw.Draw(image)
            width = 30
            fontsize = 600
            for i in range(num_chunks):
                draw.rectangle(((x[i]-chunk_width/2)/2,image.height-(y[i]+chunk_height/2)/2,(x[i]+chunk_width/2)/2,image.height-(y[i]-chunk_height/2)/2),outline=colors[i],width=width)
                draw.text((x[i]/2, image.height-y[i]/2), str(i+1), fill=colors[i], font=ImageFont.truetype("Ubuntu-R.ttf", fontsize))
        else:
            image = fits_to_pil(data)
            draw = ImageDraw.Draw(image)
            width = 10
            fontsize = 100
            for i in range(num_chunks):
                draw.rectangle(((x[i]-chunk_width/2),image.height-(y[i]+chunk_height/2),(x[i]+chunk_width/2),image.height-(y[i]-chunk_height/2)),outline=colors[i],width=width)
                draw.text((x[i], image.height-y[i]), str(i+1), fill=colors[i], font=ImageFont.truetype("Ubuntu-R.ttf", fontsize))
        if save:
            image.save(save_dir/f'{signature}_A_chunks.jpg',"JPEG",quality=85,optimize=True)
        if play_through:
            tk_display(image,'Chunks')

    for i in range(num_chunks):
        chunk = f"chunk{i+1}"
        if verbosity > 0:
            print(f"  cutting out {chunk}...")
        data_cutout = Cutout2D(data, position=(x[i],y[i]), size=(chunk_height,chunk_width), wcs=wcs, mode='strict')
        header.update(data_cutout.wcs.to_header())
        fits.writeto(data_out_folder/f'{signature}_{chunk}.fits', data_cutout.data, header, overwrite=True)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Cuts tile into chunks (both data and weight).')
    parser.add_argument('data_in_file', help='Input data tile')
    parser.add_argument('data_out_folder', help='Output folder for data chunks')
    parser.add_argument('chunkinfo_json', help='JSON file containing info about the chunk dimensions and locations.')
    parser.add_argument('-jpeg_in_file', help='The filename of the input jpeg (for save=True).')
    parser.add_argument('-jpeg_out_file', help='The filename of the output jpeg (for save=True).')
    parser.add_argument('--save', action='store_true', default=False, help='Saves a diagram showing the chunks overlaid on the jpeg specified in "jpeg_in_file".')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', default=1, choices=[0,1,2], help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    
    chunk(args.data_in_file,args.data_out_folder,args.chunkinfo_json,args.jpeg_in_file,args.jpeg_out_file,save=args.save,signature=args.signature,verbosity=args.verbosity)