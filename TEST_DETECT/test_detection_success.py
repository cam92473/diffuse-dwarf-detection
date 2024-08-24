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
from astropy.io import fits
import numpy as np

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
    clipped_dir = input_dir/'preprocessed_images'/'artificial'/'clipped'
    clipped_file = clipped_dir/f'{signature}_clp.fits'
    gimpready_dir = input_dir/'preprocessed_images'/'artificial'/'clipped'/'gimp_ready'
    gimpready_file = gimpready_dir/f'{signature}_clp_gmp.fits'
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
             "clipped":clipped_dir,
             "clipped_file": clipped_file,
             "gimpready":gimpready_dir,
             "gimpready_file":gimpready_file,
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

def test_detection_success(data_path,psf_path,mag,reff,n,q,theta,x0,y0,medblur_rad,detect_params,save,play_through,verbosity):
 
    tA = time.perf_counter()

    signature = create_signature(data_path,f'dw_{mag}_{reff}')
    paths = configure_paths(data_path,medblur_rad,save,signature)

    if verbosity > 0:
        print("inserting dwarf...")
    insert_dwarf_intofile(data_path,psf_path,mag,reff,n,q,theta,x0,y0,paths["raw_file"])
    if verbosity > 0:
        print("done")
    
    if verbosity > 0:
        print("preprocessing image...")
    preprocess_image(paths["raw_file"],True,True)
    if verbosity > 0:
        print("done")

    if verbosity > 0:
        print("performing detection...")

    flush_dirs([paths["blurred"],paths["csv"],paths["images"],paths["cutouts"]])
    
    t1 = time.perf_counter()
    if verbosity > 0:
        print("starting algorithm")

    mask_blur(paths["gimpready_file"], paths, medblur_rad, save, play_through, signature, verbosity)
    detect_filter_cutout(paths["blurred_file"], paths, detect_params, save, play_through, signature, verbosity)
    success = evaluate_success(x0,y0,reff,paths,signature)

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"finished algorithm, time taken: {t2-t1}")

    if success:
        print(f"\n Successfully detected dwarf with magnitude {mag} and reff {reff}\n")
    else:
        print(f"\n Failed to detect dwarf with magnitude {mag} and reff {reff}\n")

    tB = time.perf_counter()
    if verbosity > 0:
        print(f"finished testing, time taken: {tB-tA}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_path', help='Input image. May be from one of the RAW subdirectories, in which case it needs to be preprocessed, or from the PREPROCESS/preprocessed directory, in which case it can be directly input to the algorithm.')
    parser.add_argument('psf_path', help='Filename of the PSF with which to convolve the dwarf.')
    parser.add_argument('mag', type=float, help='Apparent magnitude.')
    parser.add_argument('reff', type=float, help='Effective or half-light radius, in pixels.')
    parser.add_argument('n', type=float, help='Sersic index.')
    parser.add_argument('q', type=float, help='Axis ratio. Note: axis ratio = 1 - ellipticity. (an axis ratio of 1 describes a radially-symmetric dwarf)')
    parser.add_argument('theta', type=float, help='Rotation angle, in degrees.')
    parser.add_argument('x0', type=float,  help='x position in pixels.')
    parser.add_argument('y0', type=float, help='y position in pixels.')
    parser.add_argument('-medblur_rad', default=20, type=int, help='Radius of the circular kernel used by Gimp to median blur the image. Best results obtained when the blurring kernel is about the size of a dwarf galaxy.')
    parser.add_argument('-detect_params', nargs=2, default=[500,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the blurred image.')
    parser.add_argument('--save', action='store_true', help='Saves images captured from the algorithm\'s run to the saved_runs directory, allowing you to inspect them after the algorithm has finished.')
    parser.add_argument('--play_through', action='store_true', help='Executes the algorithm in play-through mode, allowing you to observe the algorithm working in "real time" (through the Gimp UI). If the image is very big, the program might become EXTREMELY slow.')
    parser.add_argument('--verbosity', type=int, default=1, help='Verbosity level controlling the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data_path = Path(args.data_path).resolve()
    psf_path = Path(args.psf_path).resolve()
    mag = args.mag
    reff = args.reff
    n = args.n
    q = args.q
    theta = args.theta
    x0 = args.x0
    y0 = args.y0
    medblur_rad = args.medblur_rad
    detect_params = args.detect_params
    save = args.save
    play_through = args.play_through
    verbosity = args.verbosity    

    test_detection_success(data_path,psf_path,mag,reff,n,q,theta,x0,y0,medblur_rad,detect_params,save,play_through,verbosity)

