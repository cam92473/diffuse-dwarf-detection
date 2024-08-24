import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from ALGORITHM.MASK_BLUR.mask_blur import mask_blur
from ALGORITHM.DETECT_FILTER_CUTOUT.detect_filter_cutout import detect_filter_cutout
from artificial_dwarf.insert_dwarf import insert_dwarf_intofile
import time
from input_images.preprocess import preprocess_image
from datetime import datetime
import os
import argparse
import re
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits

def evaluate_success(x0,y0,reff,paths,signature):
    with fits.open(paths["images"]/f'{signature}_filtered_detections.fits') as hdul:
        segmap = hdul[0].data
    segmap[segmap>0] = 1
    segmap = segmap.astype(bool)
    circle = np.zeros_like(segmap)
    i0 = int(y0-1)
    j0 = int(x0-1)
    for i in range(circle.shape[0]):
        for j in range(circle.shape[1]):
            if ((i-i0)**2 + (j-j0)**2) < (reff//3)**2:
                circle[i,j] = 1
    circle = circle.astype(bool)
    '''import matplotlib.pyplot as plt
    plt.imshow(circle)
    plt.show()
    plt.imshow(segmap)
    plt.show()'''
    success = False
    if (segmap & circle).sum() > 0:
        success = True
    return success

def flush_dirs(dirs_to_clean):
    for dir in dirs_to_clean:
        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            os.unlink(file_path)

def create_signature(data_path,signature):
    if signature is None:
        timestr = datetime.now().strftime("_%Y%m%d%H%M%S")
        signature = data_path.stem + timestr
    return signature

def configure_paths(data_path,medblur_rad,save,signature):
    testdet_dir = Path.cwd()
    root_dir = testdet_dir.parent
    algm_dir = root_dir/'ALGORITHM'
    input_dir = root_dir/'input_images'
    raw_dir = input_dir/'raw_images'/'artificial'
    raw_file = raw_dir/f'{signature}.fits'
    raw_album = raw_dir/'album'
    clipped_dir = input_dir/'preprocessed_images'/'artificial'/'clipped'
    clipped_file = None
    clipped_album = clipped_dir/'album'
    gimpready_dir = input_dir/'preprocessed_images'/'artificial'/'clipped'/'gimp_ready'
    gimpready_file = None
    gimpready_album = gimpready_dir/'album'
    mb_dir = algm_dir/'MASK_BLUR'
    blurred_dir = mb_dir/'blurred'
    blurred_file = blurred_dir/f'{signature}_blur{medblur_rad}.fits'
    gimpproc_dir = mb_dir/'gimp_procedure'
    dfc_dir = algm_dir/'DETECT_FILTER_CUTOUT'
    sextr_dir = dfc_dir/'sextractor'
    csv_dir = dfc_dir/'csv'
    images_dir = dfc_dir/'images'
    cutouts_dir = dfc_dir/'cutouts'
    sr_dir = algm_dir/'saved_runs'
    save_dir = sr_dir/signature
    if save:
        save_dir.mkdir(exist_ok=True)

    paths = {"data_file":data_path,
             "ROOT":root_dir,
             "ALGORITHM":algm_dir,
             "input_images":input_dir,
             "raw":raw_dir,
             "raw_file":raw_file,
             "raw_album":raw_album,
             "clipped":clipped_dir,
             "clipped_file": clipped_file,
             "clipped_album":clipped_album,
             "gimpready":gimpready_dir,
             "gimpready_file":gimpready_file,
             "gimpready_album":gimpready_album,
             "MASK_BLUR":mb_dir,
             "blurred":blurred_dir,
             "blurred_file":blurred_file,
             "gimp_procedure":gimpproc_dir,
             "DETECT_FILTER_CUTOUT":dfc_dir,
             "sextractor":sextr_dir,
             "csv":csv_dir,
             "images":images_dir,
             "cutouts":cutouts_dir,
             "saved_runs":sr_dir,
             "save":save_dir,
             }

    return paths

def extract_numbers(filename):
    numbers = re.findall(r"[-+]?(?:\d*\.*\d+)",filename)
    return float(numbers[0]), float(numbers[1])

def build_album(data_path,psf_path,raw_album_folder,mag,reff,n,q,theta,x0,y0,verbosity):

    if verbosity > 0:
        print("inserting dwarfs to build album...")

    for i in range(mag.size):
        for j in range(reff.size):
            outname = Path(raw_album_folder/f'dw_{mag[i]}_{reff[j]}.fits')
            insert_dwarf_intofile(data_path,psf_path,mag[i],reff[j],n,q,theta,x0,y0,outname)

    if verbosity > 0:
        print("done")

def create_ds_plot(data_path,psf_path,mag_lo,mag_hi,mag_step,reff_lo,reff_hi,reff_step,n,q,theta,x0,y0,medblur_rad,detect_params,verbosity):
 
    tA = time.perf_counter()

    save = False
    play_through = False

    signature = create_signature(data_path,f'test_detection_success')
    paths = configure_paths(data_path,medblur_rad,save,signature)
    flush_dirs([paths["raw_album"],paths["clipped_album"],paths["gimpready_album"]])

    mag = np.round(np.arange(mag_lo,mag_hi,mag_step),2)
    reff = np.round(np.arange(reff_lo,reff_hi,reff_step),2)

    if verbosity > 0:
        print("magnitudes: ",mag)
        print("number of magnitudes: ",mag.size)
        print("radii: ",reff)
        print("number of radii: ",reff.size)
    build_album(data_path,psf_path,paths["raw_album"],mag,reff,n,q,theta,x0,y0,verbosity)
    
    if verbosity > 0:
        print("preprocessing images...")
    for file in paths["raw_album"].rglob("*"):
        preprocess_image(file,True,True)
    if verbosity > 0:
        print("done")

    files = []
    for file in paths["clipped_album"].rglob("*"):
        files.append(file)
    sorted_clipped_album = sorted([str(i) for i in files], key=extract_numbers)
    files = []
    for file in paths["gimpready_album"].rglob("*"):
        files.append(file)
    sorted_gimpready_album = sorted([str(i) for i in files], key=extract_numbers)

    detect_success = np.zeros((mag.size,reff.size),dtype=bool)

    if verbosity > 0:
        print("performing detection...")

    for i in range(mag.size):
        for j in range(reff.size):
            if verbosity>0:
                print(f"mag {mag[i]} reff {reff[j]}")
            
            t1 = time.perf_counter()
            if verbosity > 0:
                print("starting algorithm")

            paths["gimpready_file"] = Path(sorted_gimpready_album[reff.size*i+j])
            paths["clipped_file"] = Path(sorted_clipped_album[reff.size*i+j])
            flush_dirs([paths["blurred"],paths["csv"],paths["images"],paths["cutouts"]])

            mask_blur(paths["gimpready_file"], paths, medblur_rad, save, play_through, signature, verbosity)
            detect_filter_cutout(paths["blurred_file"], paths, detect_params, save, play_through, signature, verbosity)
            success = evaluate_success(x0,y0,reff[j],paths,signature)

            detect_success[i,j] = success

            if success:
                if verbosity>0:
                    print(f"\n Successfully detected dwarf with magnitude {mag[i]} and reff {reff[j]}\n")
            else:
                if verbosity>0:
                    print(f"\n Failed to detect dwarf with magnitude {mag[i]} and reff {reff[j]}\n")

            t2 = time.perf_counter()
            if verbosity > 0:
                print(f"finished algorithm, time taken: {t2-t1}")

    tB = time.perf_counter()
    if verbosity > 0:
        print(f"finished testing, time taken: {tB-tA}")

    plt.figure(figsize=(16,8))
    plt.imshow(detect_success.T)
    plt.ylabel('reff')
    plt.xlabel('mag')
    plt.yticks(np.arange(0,reff.size,2),labels=reff[::2].astype(int))
    plt.xticks(np.arange(0,mag.size,2),labels=mag[::2])
    plt.gca().invert_yaxis()
    plt.tight_layout()
    fig = plt.gcf()
    plt.show()
    fig.savefig('detection_success.png')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_path', help='Input image. May be from one of the RAW subdirectories, in which case it needs to be preprocessed, or from the PREPROCESS/preprocessed directory, in which case it can be directly input to the algorithm.')
    parser.add_argument('psf_path', help='Filename of the PSF with which to convolve the dwarf.')
    parser.add_argument('mag_lo', type=float, help='Lower bound for range for apparent magnitudes.')
    parser.add_argument('mag_hi', type=float, help='Upper bound for range for apparent magnitudes.')
    parser.add_argument('mag_step', type=float, help='Step size for range for apparent magnitudes.')
    parser.add_argument('reff_lo', type=float, help='Lower bound for range for effective or half-light radii, in pixels.')
    parser.add_argument('reff_hi', type=float, help='Upper bound for range for effective or half-light radii, in pixels.')
    parser.add_argument('reff_step', type=float, help='Step size for range for effective or half-light radii, in pixels.')
    parser.add_argument('n', type=float, help='constant sersic index.')
    parser.add_argument('q', type=float, help='constant axis ratio. Note: axis ratio = 1 - ellipticity. (an axis ratio of 1 describes a radially-symmetric dwarf)')
    parser.add_argument('theta', type=float, help='constant rotation angle, in degrees.')
    parser.add_argument('x0', type=float,  help='constant x position in pixels.')
    parser.add_argument('y0', type=float, help='constant y position in pixels.')
    parser.add_argument('-medblur_rad', default=20, type=int, help='Radius of the circular kernel used by Gimp to median blur the image. Best results obtained when the blurring kernel is about the size of a dwarf galaxy.')
    parser.add_argument('-detect_params', nargs=2, default=[500,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the blurred image.')
    parser.add_argument('--verbosity', type=int, default=1, help='Verbosity level controlling the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data_path = Path(args.data_path).resolve()
    psf_path = Path(args.psf_path).resolve()
    mag_lo = args.mag_lo
    mag_hi = args.mag_hi
    mag_step = args.mag_step
    reff_lo = args.reff_lo
    reff_hi = args.reff_hi
    reff_step = args.reff_step
    n = args.n
    q = args.q
    theta = args.theta
    x0 = args.x0
    y0 = args.y0
    medblur_rad = args.medblur_rad
    detect_params = args.detect_params
    verbosity = args.verbosity    

    create_ds_plot(data_path,psf_path,mag_lo,mag_hi,mag_step,reff_lo,reff_hi,reff_step,n,q,theta,x0,y0,medblur_rad,detect_params,verbosity)

