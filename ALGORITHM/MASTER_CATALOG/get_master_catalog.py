import argparse
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from scipy.spatial import cKDTree
import pandas as pd
import warnings
from datetime import datetime
from pathlib import Path
import colorsys
from astropy.stats import sigma_clip
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
import csv

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

def create_signature(data_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{data_file.stem}_{timestr}"
    return signature

def get_detection_mask(data):
    mask = np.isnan(data)
    edges = np.insert(np.diff(mask,axis=0),0,np.zeros(mask.shape[1]),axis=0) | np.insert(np.diff(mask,axis=1),0,np.zeros(mask.shape[0]),axis=1)
    rr, cc = np.mgrid[0:data.shape[0],0:data.shape[1]]
    edge_coords = np.array((rr[edges],cc[edges])).T
    for coord in edge_coords:
        mask[coord[0]-257:coord[0]+257,coord[1]-257:coord[1]+257] = True
    mask[:256,:] = True
    mask[-256:,:] = True
    mask[:,:256] = True
    mask[:,-256:] = True
    return ~mask

def get_master_catalog(data_file,is_tile,detection_mask,injected_coords,injected_params,known_dwarfs,initial_completeness_csv,csv_dir,master_catalog_dir,tile_color_jpeg,save_dir,save=False,play_through=False,signature=None,verbosity=1):

    signature = create_signature(data_file,signature)

    filtered_csvs = list(csv_dir.glob("*_filtered_detections.csv"))
    master_catalog = pd.DataFrame(columns=['CHUNK','ALPHA_J2000','DELTA_J2000'])
    warnings.simplefilter(action='ignore', category=FutureWarning)
    for i, fcsv in enumerate(filtered_csvs):
        df = pd.read_csv(fcsv)
        df['CHUNK'] = i+1
        master_catalog = pd.concat([master_catalog,df[['CHUNK','ALPHA_J2000','DELTA_J2000']]],ignore_index=True)
    master_catalog.columns = ['CHUNK','RA_det', 'DEC_det']
    num_detections = len(master_catalog)
    if verbosity > 0:
        print(f"  Total detected objects (including possible duplicates): {num_detections}")

    with fits.open(data_file) as hdul:
        data = hdul[0].data
        header = hdul[0].header
    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']

    x, y = SkyCoord(master_catalog['RA_det'],master_catalog['DEC_det'],unit="deg").to_pixel(wcs)
    master_catalog['X_det'] = x
    master_catalog['Y_det'] = y

    if detection_mask is None:
        detection_mask = get_detection_mask(data)
    else:
        detection_mask = np.load(detection_mask)
    master_catalog = master_catalog[detection_mask[y.astype(int), x.astype(int)]].reset_index(drop=True)

    xy_coords = master_catalog[['X_det', 'Y_det']].values
    tree = cKDTree(xy_coords)
    tolerance = 20
    pairs = tree.query_pairs(r=tolerance)
    duplicate_idx = set()

    for j, k in pairs:
        if master_catalog.iloc[j,0] != master_catalog.iloc[k,0]:
            duplicate_idx.add(j)

    duplicates_catalog = master_catalog.iloc[list(duplicate_idx)].reset_index(drop=True)
    num_duplicates = len(duplicates_catalog)
    master_catalog_unique = master_catalog.drop(list(duplicate_idx)).reset_index(drop=True)
    num_unique_detections = len(master_catalog_unique)

    if verbosity > 0:
            print(f"  Removed {num_duplicates} duplicate skycoords from catalog ({num_unique_detections} remaining)")

    if (save | play_through):
        num_chunks = master_catalog['CHUNK'].max()
        color_coords = [round(t[i] * 255) for t in [colorsys.hsv_to_rgb(h, 1, 1) for h in [i/num_chunks for i in list(range(0,num_chunks))]] for i in range(3)]
        colors = list(zip(color_coords[::3],color_coords[1::3],color_coords[2::3]))
        if is_tile:
            Image.MAX_IMAGE_PIXELS = np.inf
            image = Image.open(tile_color_jpeg)
            image = image.resize((image.width // 2, image.height // 2))
            draw = ImageDraw.Draw(image)
            for i in range(num_chunks):
                mc_chunki = master_catalog[master_catalog['CHUNK']==i+1]
                for j in range(len(mc_chunki)):
                    draw.text((mc_chunki['X_det'].iloc[j]/2, image.height-mc_chunki['Y_det'].iloc[j]/2), "+", fill=colors[i], font=ImageFont.truetype("Ubuntu-R.ttf", 200), anchor="mm")
            for k in range(len(duplicates_catalog)):
                draw.ellipse([((duplicates_catalog['X_det'].iloc[k]-200)/2,image.height-(duplicates_catalog['Y_det'].iloc[k]+200)/2), ((duplicates_catalog['X_det'].iloc[k]+200)/2,image.height-(duplicates_catalog['Y_det'].iloc[k]-200)/2)], outline="white", width=20)
        else:
            image = fits_to_pil(data)
            draw = ImageDraw.Draw(image)
            for i in range(num_chunks):
                mc_chunki = master_catalog[master_catalog['CHUNK']==i+1]
                for j in range(len(mc_chunki)):
                    draw.text((mc_chunki['X_det'].iloc[j], image.height-mc_chunki['Y_det'].iloc[j]), "+", fill=colors[i], font=ImageFont.truetype("Ubuntu-R.ttf", 100), anchor="mm")
            for k in range(len(duplicates_catalog)):
                draw.ellipse([(duplicates_catalog['X_det'].iloc[k]-50,image.height-(duplicates_catalog['Y_det'].iloc[k]+50)), (duplicates_catalog['X_det'].iloc[k]+50,image.height-(duplicates_catalog['Y_det'].iloc[k]-50))], outline="white", width=10)
        if save:
            image.save(save_dir/f"{signature}_H_duplicate_removal.jpeg","JPEG",quality=85,optimize=True)
        if play_through:
            tk_display(image,'Duplicate detection removal')

    if injected_coords is not None:
        detected_coords = master_catalog_unique[['X_det', 'Y_det']].values
        tol = 40

        tree = cKDTree(detected_coords)
        matches = tree.query_ball_point(injected_coords,tol)
        matched = np.array([len(match) > 0 for match in matches])
        completeness = np.sum(matched)/len(injected_coords)
        if verbosity > 0:
            print(f" Completeness: {completeness*100:.2f}%")
        with open(initial_completeness_csv, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(np.append(injected_params,completeness))

        tree = cKDTree(injected_coords)
        matches = tree.query_ball_point(detected_coords,tol)
        matched = np.array([len(match) > 0 for match in matches])
        master_catalog_unique['injected_dwarf'] = matched

        known_dwarfs = pd.read_csv(known_dwarfs)
        known_dwarf_coords = known_dwarfs[['X', 'Y']].values
        tree = cKDTree(known_dwarf_coords)
        matches = tree.query_ball_point(detected_coords,tol)
        matched = np.array([len(match) > 0 for match in matches])
        master_catalog_unique['real_dwarf'] = matched

        if (save | play_through):
            if is_tile:
                Image.MAX_IMAGE_PIXELS = np.inf
                image = Image.open(tile_color_jpeg)
                image = image.resize((image.width // 2, image.height // 2))
                draw = ImageDraw.Draw(image)
                for i in range(len(known_dwarf_coords)):
                    draw.text((known_dwarf_coords[i,0]/2, image.height-known_dwarf_coords[i,1]/2), "+", fill="lime", font=ImageFont.truetype("Ubuntu-R.ttf", 200), anchor="mm")
                for i in range(len(injected_coords)):
                    draw.text((injected_coords[i,0]/2, image.height-injected_coords[i,1]/2), "+", fill="red", font=ImageFont.truetype("Ubuntu-R.ttf", 200), anchor="mm")
                for i in range(len(detected_coords)):
                    draw.text((detected_coords[i,0]/2, image.height-detected_coords[i,1]/2), "x", fill="blue", font=ImageFont.truetype("Ubuntu-R.ttf", 200), anchor="mm")
                mc_idw = master_catalog_unique[master_catalog_unique['injected_dwarf']==True]
                for i in range(len(mc_idw)):
                    draw.text((mc_idw['X_det'].iloc[i]/2, image.height-mc_idw['Y_det'].iloc[i]/2), "O", fill="purple", font=ImageFont.truetype("Ubuntu-R.ttf", 200), anchor="mm")
            else:
                image = fits_to_pil(data)
                draw = ImageDraw.Draw(image)
                for i in range(len(known_dwarf_coords)):
                    draw.text((known_dwarf_coords[i,0], image.height-known_dwarf_coords[i,1]), "+", fill="lime", font=ImageFont.truetype("Ubuntu-R.ttf", 100), anchor="mm")
                for i in range(len(injected_coords)):
                    draw.text((injected_coords[i,0], image.height-injected_coords[i,1]), "+", fill="red", font=ImageFont.truetype("Ubuntu-R.ttf", 100), anchor="mm")
                for i in range(len(detected_coords)):
                    draw.text((detected_coords[i,0], image.height-detected_coords[i,1]), "x", fill="blue", font=ImageFont.truetype("Ubuntu-R.ttf", 100), anchor="mm")
                mc_idw = master_catalog_unique[master_catalog_unique['injected_dwarf']==True]
                for i in range(len(mc_idw)):
                    draw.text((mc_idw['X_det'].iloc[i], image.height-mc_idw['Y_det'].iloc[i]), "O", fill="purple", font=ImageFont.truetype("Ubuntu-R.ttf", 100), anchor="mm")
            if save:
                image.save(save_dir/f"{signature}_I_detection_success_rate.jpeg","JPEG",quality=85,optimize=True)
            if play_through:
                tk_display(image,'Detection success rate')

    master_catalog_unique.to_csv(master_catalog_dir/f"{signature}_master_catalog.csv",index=False)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Compiles a master catalog from smaller catalogs of detections and removes duplicate coordinates.')
    parser.add_argument('data_file', help='Data file associated with the detections across all of the smaller catalogs.')
    parser.add_argument('csv_dir', help='Directory containing all of the smaller catalog csvs.')
    parser.add_argument('master_catalog_dir', help='Directory where you wish to create the master catalog csv.')
    parser.add_argument('-save_dir', help='Directory where you wish to save the produced plot showing the duplicate coordinates.')
    parser.add_argument('--save', action='store_true', default=False, help='Saves jpegs showing various stages of the algorithm operating on the image. These jpegs are saved to a single folder.')
    parser.add_argument('--play_through', action='store_true', default=False, help='Executes the algorithm in play-through mode, allowing you to observe the algorithm working in "real time" (through the Gimp UI). Do not use if the image is very big or a huge slowdown will occur.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=[0,1,2], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data_file = Path(args.data_file).resolve()
    csv_dir = Path(args.csv_dir).resolve()
    master_catalog_dir = Path(args.master_catalog_dir).resolve()
    save_dir = Path(args.save_dir).resolve()
    save = args.save
    play_through = args.play_through
    signature = args.signature
    verbosity = args.verbosity
    
    get_master_catalog(data_file,csv_dir,master_catalog_dir,save_dir,save=save,play_through=play_through,signature=signature,verbosity=verbosity)
