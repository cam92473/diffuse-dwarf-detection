import argparse
import time
import subprocess
from pathlib import Path
import numpy as np
from scipy.ndimage import median_filter
from astropy.io import fits

def blur_image(filt_dir, photfilt, kernelrad, signature, verbose):
    
    t1 = time.perf_counter()

    masked_path = str(filt_dir/f'{signature}_3_data_masked_{photfilt}.fits')
    binned_path = str(filt_dir/f'{signature}_4_blurred_{photfilt}.fits')
    subprocess.call(f"flatpak run org.gimp.GIMP -idf -b '(python-fu-median-blur RUN-NONINTERACTIVE \"{masked_path}\" {kernelrad} \"{binned_path}\")'", stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, shell=True)

    t2 = time.perf_counter()
    if verbose:
        print(f"blurring {photfilt}: {t2-t1}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('filename', help='Filename of the data image, including the .fits extension.')
    parser.add_argument('windowindowsize', type=int, help='Window (bin) sizes for the pixels. The image is divided into square windows and the median of the pixels within each window is written to a single pixel in the output image. Supply this argument as the sidelength of the desired square window. More than one window sidelength can be provided, and for each ')
    parser.add_argument('dolog', default=True)
    parser.add_argument('testonimage', default=False, help='Set to true if you are testing this on a non-fits image.')
    parser.add_argument('verbose', default=True)
    parser.add_argument('wheresave', default=None)

    args = parser.parse_args()
    filename = args.filename
    windowindowsize = args.windowindowsize
    dolog = args.dolog
    testonimage = args.testonimage
    verbose = args.verbose
    wheresave = args.wheresave

    blur_image(filename,windowindowsize,dolog,testonimage,verbose,wheresave)


    '''
    LEGACY CODE
    
    #gimp_blur = f'image = pdb.file_fits_load("{masked_path}", "{masked_path}");active_layer = pdb.gimp_image_get_active_layer(image);pdb.python_gegl(image, active_layer, "median-blur radius={kernelrad} percentile=50 high-precision=1")'
    blur_path = str(Path.cwd()/'detection')
    stuff = subprocess.check_output(f"flatpak run org.gimp.GIMP -idf --batch-interpreter python-fu-eval -b 'import sys;sys.path.append(\"{blur_path}\");import gimp_median_blur as gmb;gmb.gimp_median_blur(\"{masked_path}\",{kernelrad})' -b 'pdb.gimp_quit(1)'", stdout=dev.NULL, shell=True)    
    

    kernel = np.ones((61,61),dtype=np.uint8)
    for i in range(61):
        for j in range(61):
            if (30-i)**2+(30-j)**2>30**2:
                kernel[i,j] = 0

    with fits.open(masked_path) as hdul:
        data = hdul[0].data
    med = median_filter(data,footprint=kernel,mode='nearest')
    fits.writeto(str(filt_dir/f'{signature}_blurred_{photfilt}.fits'),med,overwrite=True)


    '''
