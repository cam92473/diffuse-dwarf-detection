import argparse
import time
import shutil
import os
from datetime import datetime
from pathlib import Path

def establish_output_tree(data_folder,project_root,signature):
    output_root = Path(project_root/'OUTPUT'/signature)
    if os.path.isdir(output_root):
        shutil.rmtree(output_root)
    shutil.copytree(data_folder,output_root)
    for root, dirs, files in os.walk(output_root):
        for fname in files:
            if fname.split('.')[-2] == 'weight':
                os.rename(os.path.join(root,fname),os.path.join(root,signature+f'_1b_weight_{root[-1]}.fits'))
            else:
                os.rename(os.path.join(root,fname),os.path.join(root,signature+f'_1a_data_{root[-1]}.fits'))
    return output_root

def create_signature(signature):
    if signature is None:
        timestr = datetime.now().strftime("-%Y%m%d%H%M%S")
        signature = data_folder.name + timestr
    return signature

def setup(data_folder,signature,verbose):
    t1 = time.perf_counter()

    signature = create_signature(signature)
    project_root = Path.cwd().parents[3]
    output_root = establish_output_tree(data_folder,project_root,signature)
    sex_dir = Path(project_root/'PYTHON'/'CALCULATE_ARRAYS'/'MASTER_CATALOGS'/'DETECTION'/'sextractor')
    rgb_dir = Path(project_root/'PYTHON'/'CALCULATE_ARRAYS'/'MASTER_CATALOGS'/'DETECTION'/'detection'/'rgb_image')

    t2 = time.perf_counter()
    if verbose:
        print(f"setup: {t2-t1}")

    return signature, output_root, sex_dir, rgb_dir

def cleanup(output_root,phot_filters):
    for photfilt in phot_filters:
        shutil.rmtree(output_root/photfilt)         
    
def detect_dwarfs(data_folder, phot_filters, mask_params, blur_radius, stack_mode, detect_params, save_records, cutout_detections, signature, verbose):

    t1 = time.perf_counter()

    signature, output_root, sex_dir, rgb_dir  = setup(data_folder,signature,verbose)

    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        mask_image(filt_dir, photfilt, sex_dir, mask_params, signature, verbose)
    prepare_masked_images_for_gimp(output_root,phot_filters,signature,verbose)
    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        blur_image(filt_dir, photfilt, blur_radius, signature, verbose)
    stack_blurred_images(output_root, phot_filters, stack_mode, signature, verbose)
    detect_objects(output_root, sex_dir, detect_params, signature, verbose)
    #possibly a CNN here ... could take some work

    if save_records:
        save_records_func(output_root, phot_filters, rgb_dir, signature, verbose)

    if cutout_detections:
        make_cutouts(output_root, phot_filters, rgb_dir, signature, verbose)

    #cleanup(output_root,phot_filters)

    t2 = time.perf_counter()
    if verbose:
        print(f"Detection algorithm: {t2-t1}")

if __name__ == '__main__':

    from detection.mask import mask_image
    from detection.blur import blur_image
    from detection.stack import stack_blurred_images
    from detection.detect import detect_objects
    from detection.save_records import save_records_func
    from detection.cutout import make_cutouts
    from detection.prepare_masked_images import prepare_masked_images_for_gimp

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_folder', help='Parent (root) folder containing subfolders labeled by photometric filter, each of which should contain the data image and its corresponding weight image in that filter.')
    parser.add_argument('phot_filters', help='The list of photometric filters the data is taken in. Enter as a continuous string, e.g., "griz"')
    parser.add_argument('-mask_params', nargs=2, default=[100,1], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to create a segmentation image that will become a mask for unwanted objects.')
    parser.add_argument('-blur_radius', default=30, type=int, help='Radius of the circular kernel used to median-blur the masked image.')
    parser.add_argument('-stack_mode', default='median', choices=['mean','median','min'], help='How to stack the blurred images.')
    parser.add_argument('-detect_params', nargs=2, default=[100,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the stacked image.')
    parser.add_argument('--save_records', action='store_true', help='Whether or not to save files (images, csvs) giving a record of what the algorithm did on the data. Helpful for diagnosing issues and understanding behaviour.')
    parser.add_argument('--cutout_detections', action='store_true', help='If toggled, will save small 800x800 fits cutouts of the detections, allowing you to inspect them to determine visually whether they are possible dwarfs.')
    parser.add_argument('--signature', help='Optional parameter which allows you to specify the signature, or the name used to identify the output folder and all of its files (if not specified, a name will be created based on the input data image and the current time).')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    data_folder = Path(args.data_folder).resolve()
    phot_filters = list(args.phot_filters)
    mask_params = args.mask_params
    blur_radius = args.blur_radius
    stack_mode = args.stack_mode
    detect_params = args.detect_params
    save_records = args.save_records
    cutout_detections = args.cutout_detections
    signature = args.signature
    verbose = args.verbose

    detect_dwarfs(data_folder, phot_filters, mask_params, blur_radius, stack_mode, detect_params, save_records, cutout_detections, signature, verbose)

else:

    from .detection.mask import mask_image
    from .detection.blur import blur_image
    from .detection.stack import stack_blurred_images
    from .detection.detect import detect_objects
    from detection.save_records import save_records_func
    from detection.cutout import make_cutouts
    from detection.prepare_masked_images import prepare_masked_images_for_gimp