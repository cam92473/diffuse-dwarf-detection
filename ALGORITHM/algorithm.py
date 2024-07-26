import argparse
import time
from datetime import datetime
from pathlib import Path
import os

def flush_dirs(dirs_to_clean):
    for dir in dirs_to_clean:
        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            os.unlink(file_path)

def create_signature(signature):
    if signature is None:
        timestr = datetime.now().strftime("_%Y%m%d%H%M%S")
        signature = data_path.stem + timestr
    return signature

def setup(data_path,medblur_rad,signature,save):
    signature = create_signature(signature)
    algm_dir = Path.cwd()
    root_dir = algm_dir.parent  
    input_dir = root_dir/'input_images'
    clipped_dir = input_dir/'preprocessed_images'/'clipped'
    clipped_file = clipped_dir/(data_path.stem[:-4]+data_path.suffix)
    gimpready_dir = input_dir/'preprocessed_images'/'clipped'/'gimp_ready'
    mb_dir = algm_dir/'MASK_BLUR'
    blurred_dir = mb_dir/'blurred'
    blurred_file = blurred_dir/f'{signature}_blur{medblur_rad}.fits'
    gimpproc_dir = mb_dir/'gimp_procedure'
    dfc_dir = algm_dir/'DETECT_FILTER_CUTOUT'
    sextr_dir = dfc_dir/'sextractor'
    csv_dir = dfc_dir/'csv'
    images_dir = dfc_dir/'images'
    cutouts_dir = dfc_dir/'cutouts'
    cnn_dir = algm_dir/'CONSULT_CNN'
    dwarf_dir = cnn_dir/'dwarf'
    nondwarf_dir = cnn_dir/'nondwarf'
    sr_dir = algm_dir/'saved_runs'
    save_dir = sr_dir/signature
    if save:
        save_dir.mkdir(exist_ok=True)

    flush_dirs([blurred_dir,csv_dir,images_dir,cutouts_dir,dwarf_dir,nondwarf_dir])

    paths = {"data_file":data_path,
             "ROOT":root_dir,
             "ALGORITHM":algm_dir,
             "input_images":input_dir,
             "clipped":clipped_dir,
             "clipped_file": clipped_file,
             "gimp_ready":gimpready_dir,
             "MASK_BLUR":mb_dir,
             "blurred":blurred_dir,
             "blurred_file":blurred_file,
             "gimp_procedure":gimpproc_dir,
             "DETECT_FILTER_CUTOUT":dfc_dir,
             "sextractor":sextr_dir,
             "csv":csv_dir,
             "images":images_dir,
             "cutouts":cutouts_dir,
             "CONSULT_CNN":cnn_dir,
             "dwarf":dwarf_dir,
             "nondwarf":nondwarf_dir,
             "saved_runs":sr_dir,
             "save":save_dir,
             }

    return signature, paths

def detect_dwarfs(data_path, medblur_rad, detect_params, save, play_through, signature, verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print("Starting algorithm")

    signature, paths = setup(data_path,medblur_rad,signature,save)
    mask_blur(paths, medblur_rad, save, play_through, signature, verbosity)
    detect_filter_cutout(paths, detect_params, save, play_through, signature, verbosity)
    consult_CNN(paths, verbosity)

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"Finished algorithm, total time: {t2-t1}")

if __name__ == '__main__':

    from MASK_BLUR.mask_blur import mask_blur
    from DETECT_FILTER_CUTOUT.detect_filter_cutout import detect_filter_cutout
    from CONSULT_CNN.consult_CNN import consult_CNN

    parser = argparse.ArgumentParser(description='Dwarf detection algorithm')
    parser.add_argument('data_path', help='Input image. May be from one of the RAW subdirectories, in which case it needs to be preprocessed, or from the PREPROCESS/preprocessed directory, in which case it can be directly input to the algorithm.')
    parser.add_argument('-medblur_rad', default=30, type=int, help='Radius of the circular kernel used by Gimp to median blur the image. Best results obtained when the blurring kernel is about the size of a dwarf galaxy.')
    parser.add_argument('-detect_params', nargs=2, default=[100,2], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the blurred image.')
    parser.add_argument('--save', action='store_true', help='Saves images captured from the algorithm\'s run to the saved_runs directory, allowing you to inspect them after the algorithm has finished.')
    parser.add_argument('--play_through', action='store_true', help='Executes the algorithm in play-through mode, allowing you to observe the algorithm working in "real time" (through the Gimp UI). If the image is very big, the program might become EXTREMELY slow.')
    parser.add_argument('--signature', help='Optional parameter which allows you to specify the signature, or the name used to identify the output files (if not specified, a name will be created based on the input data name and the current time).')
    parser.add_argument('--verbosity', type=int, default=1, help='Verbosity level controlling the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data_path = Path(args.data_path).resolve()
    medblur_rad = args.medblur_rad
    detect_params = args.detect_params
    save = args.save
    play_through = args.play_through
    signature = args.signature
    verbosity = args.verbosity

    if data_path.parent.stem != "gimp_ready":
        raise Exception("The image must be preprocessed (sigma clipped and made ready for Gimp) before the algorithm can operate on it. Use preprocess.py in the 'input_images' directory.")

    detect_dwarfs(data_path, medblur_rad, detect_params, save, play_through, signature, verbosity)

else:

    '''from .detection.mask import mask_image
    from .detection.blur import blur_image
    from .detection.stack import stack_blurred_images
    from .detection.detect import detect_objects
    from detection.save_records import save_records_func
    from detection.cutout import make_cutouts
    from detection.prepare_masked_images import prepare_masked_images_for_gimp'''