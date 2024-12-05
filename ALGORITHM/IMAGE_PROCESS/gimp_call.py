import time
import subprocess
import sys
import os
from astropy.io import fits
from datetime import datetime
import argparse
from pathlib import Path

def restock_WCS(processed_file,data_file,verbosity):
    if verbosity > 0:
        print("   restocking WCS...")
    with fits.open(data_file) as hdul:
        header_with_wcs = hdul[0].header
    with fits.open(processed_file,mode='update') as hdul:
        hdul[0].header = header_with_wcs

def configure_bash(play_through,verbosity):
    if play_through:
        switch = '-df'
    else:
        switch = '-idf'
    if verbosity == 0:
        stdout = open(os.devnull, 'w')
        stderr = open(os.devnull, 'w')
    elif verbosity > 0:
        stdout = sys.stdout
        stderr = open(os.devnull, 'w')
    
    return switch, stdout, stderr,

def create_signature(data_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{data_file.stem}_{timestr}"
    return signature

def gimp_call(data_file, weight_file, processed_file, save_dir, gimpproc_dir, medblur_radius, name="", save=False, play_through=False, signature=None, verbosity=1):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(f"  Image processing{name}...")

    signature = create_signature(data_file,signature)
    switch, stdout, stderr = configure_bash(play_through,verbosity)
    python_fu_import_script = f"import sys; sys.path=['.']+sys.path; from gimp_procedure import gimp_procedure; gimp_procedure('{data_file}','{weight_file}','{processed_file}','{save_dir}',{medblur_radius},{save},{play_through},'{signature}',{verbosity})"
    subprocess.run(f"flatpak run org.gimp.GIMP {switch} --batch-interpreter python-fu-eval -b \"{python_fu_import_script}\"", cwd=gimpproc_dir, shell=True, stdout=stdout, stderr=stderr)
    restock_WCS(processed_file,data_file,verbosity)

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"  Finished image processing{name}. Total time: {t2-t1}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data_file', help='Data image.')
    parser.add_argument('weight_file', help='Weight image.')
    parser.add_argument('processed_file', help='Final processed fits file.')
    parser.add_argument('save_dir', help='Directory to save jpegs to.')
    parser.add_argument('gimpproc_dir', help='Directory containing the gimp_procedure.py module.')
    parser.add_argument('-medblur_radius', type=int, default=30, help='Radius of the circular kernel used by Gimp to median filter the image.')
    parser.add_argument('--name', default="", help='Optional argument affecting only the content of the print statements.')
    parser.add_argument('--save', action='store_true', default=False, help='Whether to save images showing the filtering steps.')
    parser.add_argument('--play_through', action='store_true', default=False, help='Toggles play-through mode, where you observe the algorithm filtering out the detections in the GIMP interface.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=[0,1,2], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data_file = Path(args.data_file).resolve()
    weight_file = Path(args.weight_file).resolve()
    processed_file = Path(args.processed_file).resolve()
    save_dir = Path(args.save_dir).resolve()
    gimpproc_dir = Path(args.gimpproc_dir).resolve()
    medblur_radius = args.medblur_radius
    name = args.name
    save = args.save
    play_through = args.play_through
    signature = args.signature
    verbosity = args.verbosity

    gimp_call(data_file,weight_file,processed_file,save_dir,gimpproc_dir,medblur_radius,name=name,save=save,play_through=play_through,signature=signature,verbosity=verbosity)