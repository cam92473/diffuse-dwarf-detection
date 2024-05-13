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
    
def get_detection_catalog(data_folder, phot_filters, surf_params, deep_params, star_params, kernelrad, det_params, save_records, cutout_detections, signature, verbose):

    t1 = time.perf_counter()

    signature, output_root, sex_dir, rgb_dir  = setup(data_folder,signature,verbose)

    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        mask_image(filt_dir, photfilt, sex_dir, surf_params, deep_params, star_params, signature, verbose)
    prepare_masked_images_for_gimp(output_root,phot_filters,signature,verbose)
    for photfilt in phot_filters:
        filt_dir = output_root/photfilt
        blur_image(filt_dir, photfilt, kernelrad, signature, verbose)
    stack_blurred_images(output_root, phot_filters, signature, verbose)
    scan_stacked_image(output_root, sex_dir, det_params, signature, verbose)
    filter_detections(output_root, signature, verbose)

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
    from detection.scan import scan_stacked_image
    from detection.filter import filter_detections
    from detection.save_records import save_records_func
    from detection.cutout import make_cutouts
    from detection.prepare_masked_images import prepare_masked_images_for_gimp

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_folder', help='Parent (root) folder containing subfolders labelled by photometric filter, each of which should contain the data image and its corresponding weight image in that filter.')
    parser.add_argument('phot_filters', help='The list of photometric filters you wish the program to consider when calculating the detections catalog. For maximum effectiveness use all the filters you have available. Enter as a string unseparated by spaces, e.g., "griz"')
    parser.add_argument('-surf_params', nargs=2, default=[100,4], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to create a segmentation map for the unwanted bright objects in the image. The scan performed by sextractor to get these objects is a "surface-level" scan, since too deep a scan will pick up dwarfs, which should not get masked. As a consequence, not all the pixels belonging to these unwanted objects will be detected in the surface scan, requiring the deep scan parameters.')
    parser.add_argument('-deep_params', nargs=2, default=[100,0.75], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to create a segmentation image for all the pixels of the unwanted objects in the surface scan. This deeper scan will pick up all the pixels of the unwanted objects, as well as the pixels of dwarfs. However, since the surface scan reveals which objects are not dwarfs, the masking procedure knows to mask out all the pixels belonging only to non-dwarfs.')
    parser.add_argument('-star_params', nargs=2, default=[20,1.5], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to create a segmentation image for stars (and incidentally some dwarfs) in the image. These objects are filtered according to size and anything the size of a star is masked out. Acts after the bright objects mask specified by surf_params and deep_params.')
    parser.add_argument('-kernelrad', default=30, type=int, help='Radius of the circular kernel used in median-filtering the masked image to expose the dwarfs.')
    parser.add_argument('-det_params', nargs=2, default=[10,5], help='Enter two numbers for the DETECT_MINAREA and DETECT_THRESH sextractor parameters used when performing detection on the binned image to obtain the raw (unfiltered) detections.')
    parser.add_argument('--save_records', action='store_true', help='Whether or not to save files (images, csvs) giving a record of what the algorithm did on the data. Helpful for diagnosing issues and understanding behaviour.')
    parser.add_argument('--cutout_detections', action='store_true', help='If toggled, will save small 800x800 fits cutouts of the detections, allowing you to inspect them to determine visually whether they are possible dwarfs.')
    parser.add_argument('--signature', help='Optional parameter which allows you to specify the signature, or the name used to identify the output folder and all of its files (if not specified, a name will be created based on the input data image and the current time).')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')


    args = parser.parse_args()
    data_folder = Path(args.data_folder).resolve()
    phot_filters = list(args.phot_filters)
    surf_params = args.surf_params
    deep_params = args.deep_params
    star_params = args.star_params
    kernelrad = args.kernelrad
    det_params = args.det_params
    save_records = args.save_records
    cutout_detections = args.cutout_detections
    signature = args.signature
    verbose = args.verbose

    get_detection_catalog(data_folder, phot_filters, surf_params, deep_params, star_params, kernelrad, det_params, save_records, cutout_detections, signature, verbose)

else:

    from .detection.mask import mask_image
    from .detection.blur import blur_image
    from .detection.stack import stack_blurred_images
    from .detection.scan import scan_stacked_image
    from .detection.filter import filter_detections
    from detection.save_records import save_records_func
    from detection.cutout import make_cutouts
    from detection.prepare_masked_images import prepare_masked_images_for_gimp