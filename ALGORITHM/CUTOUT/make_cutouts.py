from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy.nddata import Cutout2D
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk

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

def clip_and_normalize(cutout):
    warnings.filterwarnings("ignore", category=UserWarning, module="astropy.stats.sigma_clipping")
    clipped = sigma_clip(cutout,sigma=3)
    median = np.nanmedian(cutout)
    hi_mask = clipped.mask & (cutout>median)
    lo_mask = clipped.mask & (cutout<median)
    cutout[hi_mask] = np.nanmax(cutout[~clipped.mask])
    cutout[lo_mask] = np.nanmin(cutout[~clipped.mask])
    cutout -= cutout.min()
    cutout *= 65534/cutout.max()
    return np.flipud(cutout)

def create_signature(data_in_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{data_in_file.stem}_{timestr}"
    return signature

def make_cutouts(data,is_tile,master_catalog_dir,tile_color_jpeg,save_dir,cutouts_dir,save=False,play_through=False,signature=None,verbosity=1):

    master_catalog = pd.read_csv(master_catalog_dir/f"{signature}_master_catalog.csv")
    cutout_coords = np.zeros((len(master_catalog),2))
    with fits.open(data) as hdul:
        data = hdul[0].data
        wcs = WCS(hdul[0].header)
        wcs.wcs.ctype=['RA---TAN','DEC--TAN']
    
    if "injected_dwarf" in master_catalog.columns:
        generate_training_data = True
        dwarf = cutouts_dir/'dwarf'
        non_dwarf = cutouts_dir/'non_dwarf'
        dwarf.mkdir(exist_ok=True,parents=True)
        non_dwarf.mkdir(exist_ok=True,parents=True)
    else:
        generate_training_data = False
        cnn_input = cutouts_dir/'CNN_input'
        cnn_input.mkdir(exist_ok=True,parents=True)

    j = 0
    k = 0
    for i in range(len(master_catalog)):
        ra, dec = master_catalog['RA_det'].iloc[i], master_catalog['DEC_det'].iloc[i]
        cutout_coords[i] = SkyCoord(ra,dec,unit="deg").to_pixel(wcs)
        cutout = Cutout2D(data, position=cutout_coords[i], size=512, mode='strict', copy=True).data
        cutout = clip_and_normalize(cutout)
        im = Image.fromarray(np.uint16(cutout),'I;16')
        x, y = master_catalog['X_det'].iloc[i], master_catalog['Y_det'].iloc[i]
        if generate_training_data:
            is_dwarf = master_catalog['injected_dwarf'].iloc[i] | master_catalog['real_dwarf'].iloc[i]
            if is_dwarf:
                im.save(dwarf/f'{signature}_dw{j}_{int(x)}_{int(y)}.png')
                j += 1
            else:
                im.save(non_dwarf/f'{signature}_nd{k}_{int(x)}_{int(y)}.png')
                k += 1
        else:
            im.save(cnn_input/f'{signature}_co_{i}_{int(x)}_{int(y)}.png')

    if (save | play_through):
        #color_coords = [round(t[i] * 255) for t in [colorsys.hsv_to_rgb(np.random.random(), 1, 1) for hue in range(len(master_catalog))] for i in range(3)]
        #colors = list(zip(color_coords[::3],color_coords[1::3],color_coords[2::3]))
        if is_tile:
            Image.MAX_IMAGE_PIXELS = np.inf
            image = Image.open(tile_color_jpeg)
            image = image.resize((image.width // 2, image.height // 2))
            draw = ImageDraw.Draw(image)
            for i in range(len(master_catalog)):
                if generate_training_data:
                    if master_catalog['injected_dwarf'].iloc[i] | master_catalog['real_dwarf'].iloc[i]:
                        color = 'red'
                    else:
                        color = 'blue' 
                else:
                    color = 'red'
                draw.rectangle(((cutout_coords[i,0]-256)/2,image.height-(cutout_coords[i,1]+256)/2,(cutout_coords[i,0]+256)/2,image.height-(cutout_coords[i,1]-256)/2),outline=color,width=10)
        else:
            image = fits_to_pil(data)
            draw = ImageDraw.Draw(image)
            for i in range(len(master_catalog)):
                if generate_training_data:
                    if master_catalog['injected_dwarf'].iloc[i] | master_catalog['real_dwarf'].iloc[i]:
                        color = 'red'
                    else:
                        color = 'blue' 
                else:
                    color = 'red'
                draw.rectangle(((cutout_coords[i,0]-256),image.height-(cutout_coords[i,1]+256),(cutout_coords[i,0]+256),image.height-(cutout_coords[i,1]-256)),outline=color,width=5)
        if save:
            image.save(save_dir/f'{signature}_K_cutout_locations.jpg',"JPEG",quality=85,optimize=True)
        if play_through:
            tk_display(image,'Cutout locations')

