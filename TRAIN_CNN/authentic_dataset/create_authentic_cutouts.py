import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
import argparse
from astropy.io import fits
import numpy as np
from PIL import Image
from artificial_dwarf.insert_dwarf import insert_dwarf_intoarray
from artificial_dwarf.generate_parameters.generate_parameters import generate_parameters
from pathlib import Path
from astropy.stats import sigma_clip
import shutil
import math
from numpy import log10, log

def make_nondwarf_cutout(data,i,r,c,png_folder):
    cutout = data[r-256:r+256,c-256:c+256].copy()
    cutout_cc = clip_and_convert(cutout)
    im = Image.fromarray(np.uint16(cutout_cc),'I;16')
    im.save(png_folder/f'nd_{i}_{r}_{c}.png')

def print_progress_bar (iteration, total, prefix = ''):
    percent = 100 * (iteration / float(total))
    length = 40
    filledLength = int(length * iteration // total)
    bar = '█' * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent:.0f}% complete', end = '\r')
    if iteration == total: 
        print("\n")

def clip_and_convert(cutout,clip=True):
    if clip:
        clipped = sigma_clip(cutout,sigma=3)
        below = (cutout<np.median(cutout))&clipped.mask
        above = (cutout>np.median(cutout))&clipped.mask
        cutout[below] = cutout[~below].min()
        cutout[above] = cutout[~above].max()
    cutout -= cutout.min()-1
    cutout = log10(cutout)
    cutout *= 65534/cutout.max()
    return cutout

def insert_square_intoarray(data):
    data[(256-100):(256+100),(256-100):(256+100)] = np.median(data)
    return data

def make_dwarf_cutout(data,i,r,c,psf,mag,reff,n,q,theta,x0,y0,png_folder,fits_folder,save_fits,diagnostic,trivial):
    cutout = data[r-256:r+256,c-256:c+256].copy()
    if trivial:
        cutout_dw = insert_square_intoarray(cutout)
        SBeff = 0.
    else:
        cutout_dw, Ieff = insert_dwarf_intoarray(cutout,psf,mag,reff,n,q,theta,x0,y0,return_Ieff=True)
        res, zp = 0.2637, 30
        SBeff = 5*log10(res)-2.5*log10(Ieff)+zp
    if save_fits:
        fits.writeto(fits_folder/f'dw_{i}_{r}_{c}_mag{mag:.1f}_reff{reff:.1f}_n{n:.1f}_sbeff{SBeff:.1f}.fits',cutout_dw)
    cutout_dw_cc = clip_and_convert(cutout_dw)
    im = Image.fromarray(np.uint16(cutout_dw_cc),'I;16')
    im.save(png_folder/f'dw_{i}_{r}_{c}_mag{mag:.1f}_reff{reff:.1f}_n{n:.1f}_sbeff{SBeff:.1f}.png')
    if diagnostic:
        cutout = data[r-256:r+256,c-256:c+256].copy()
        blank = np.zeros(cutout.shape)
        blank_dw = insert_dwarf_intoarray(blank,psf,mag,reff,n,q,theta,x0,y0,return_Ieff=False)
        if save_fits:
            fits.writeto(fits_folder/f'dw_{i}_{r}_{c}_mag{mag:.1f}_reff{reff:.1f}_n{n:.1f}_sbeff{SBeff:.1f}_onlydwarf.fits',blank_dw)
        blank_dw_cc = clip_and_convert(blank_dw,clip=False)
        im = Image.fromarray(np.uint16(blank_dw_cc),'I;16')
        im.save(png_folder/f'dw_{i}_{r}_{c}_mag{mag:.1f}_reff{reff:.1f}_n{n:.1f}_sbeff{SBeff:.1f}_onlydwarf.png')
        if save_fits:
            fits.writeto(fits_folder/f'dw_{i}_{r}_{c}_mag{mag:.1f}_reff{reff:.1f}_n{n:.1f}_sbeff{SBeff:.1f}_onlybackground.fits',cutout)
        cutout_cc = clip_and_convert(cutout)
        im = Image.fromarray(np.uint16(cutout_cc),'I;16')
        im.save(png_folder/f'dw_{i}_{r}_{c}_mag{mag:.1f}_reff{reff:.1f}_n{n:.1f}_sbeff{SBeff:.1f}_onlybackground.png') 

def make_cutouts(data,ds_matrix,paths,valid_dw_coords,valid_nd_coords,psf,mag,reff,n,q,theta,x0,y0,diagnostic,save_fits,trivial,verbosity):

    if verbosity > 0:
        print("creating dwarf cutouts...\n")

    num_dw_cutouts = ds_matrix[0,3]
    png_folders = [paths["train_dwarf_dir"],paths["validate_dwarf_dir"],paths["test_dwarf_dir"]]
    fits_folders = [paths["train_fits_dir"],paths["validate_fits_dir"],paths["test_fits_dir"]]
    i = 0
    j = 0
    while i < num_dw_cutouts:
        r, c = np.random.randint(0,data.shape[0]), np.random.randint(0,data.shape[1])
        if valid_dw_coords[r,c]:
            make_dwarf_cutout(data,i,r,c,psf,mag[i],reff[i],n[i],q[i],theta[i],x0[i],y0[i],png_folders[j],fits_folders[j],save_fits,diagnostic,trivial)
            print_progress_bar(i,num_dw_cutouts-1,prefix=f'Dwarf {i+1}/{num_dw_cutouts}')
            i += 1
            if (i == ds_matrix.cumsum(axis=1)[0,0]) | (i == ds_matrix.cumsum(axis=1)[0,1]) | (i == ds_matrix.cumsum(axis=1)[0,2]):
                j += 1

    if verbosity > 0:
        print("creating nondwarf cutouts...\n")   

    num_nd_cutouts = ds_matrix[1,3]
    png_folders = [paths["train_nondwarf_dir"],paths["validate_nondwarf_dir"],paths["test_nondwarf_dir"]]
    i = 0
    j = 0
    while i < num_nd_cutouts:
        r, c = np.random.randint(0,data.shape[0]), np.random.randint(0,data.shape[1])
        if valid_nd_coords[r,c]:
            make_nondwarf_cutout(data,i,r,c,png_folders[j])
            print_progress_bar(i,ds_matrix[1,3]-1,prefix=f'Non-dwarf {i+1}/{ds_matrix[1,3]}')
            i += 1
            if (i == ds_matrix.cumsum(axis=1)[1,0]) | (i == ds_matrix.cumsum(axis=1)[1,1]) | (i == ds_matrix.cumsum(axis=1)[1,2]):
                j += 1
        
def configure_paths(tile,band,save_fits):

    authentic_dataset_dir = Path.cwd()
    TRAIN_CNN_dir = authentic_dataset_dir.parent
    root_dir = authentic_dataset_dir.parents[1]
    inputimages_dir = root_dir/'input_images'
    tile_dir = inputimages_dir/'tiles'/tile
    tile_data_fits = tile_dir/band/f"{tile}cut_{band}.fits"    
    artifical_dwarf_dir = root_dir/'artificial_dwarf'
    psf_fits = artifical_dwarf_dir/'psf'/'t4_dw2_g_psf.fits'
    dwarf_placement_mask_dir = authentic_dataset_dir/'dwarf_placement_mask'
    outer_mask_npy = dwarf_placement_mask_dir/'outer_mask.npy'
    total_mask_npy = dwarf_placement_mask_dir/'total_mask.npy'
    dataset_dir = authentic_dataset_dir/'dataset'
    train_dir = dataset_dir/'train'
    train_dwarfs_dir = train_dir/'dwarfs'
    train_nondwarfs_dir = train_dir/'nondwarfs'
    train_fits_dir = train_dir/'fits_files'
    validate_dir = dataset_dir/'validate'
    validate_dwarfs_dir = validate_dir/'dwarfs'
    validate_nondwarfs_dir = validate_dir/'nondwarfs'
    validate_fits_dir = validate_dir/'fits_files'
    test_dir = dataset_dir/'test'
    test_dwarfs_dir = test_dir/'dwarfs'
    test_nondwarfs_dir = test_dir/'nondwarfs'
    test_fits_dir = test_dir/'fits_files'
    dataset_paths = {"dataset_dir":dataset_dir,
                     "train_dir":train_dir,
                     "train_dwarf_dir":train_dwarfs_dir,
                     "train_nondwarf_dir":train_nondwarfs_dir,
                     "validate_dir":validate_dir,
                     "validate_dwarf_dir":validate_dwarfs_dir,
                     "validate_nondwarf_dir":validate_nondwarfs_dir,
                     "test_dir":test_dir,
                     "test_dwarf_dir":test_dwarfs_dir,
                     "test_nondwarf_dir":test_nondwarfs_dir,
                     
                     }
    optional_dataset_paths = {
        "train_fits_dir":train_fits_dir,
        "validate_fits_dir":validate_fits_dir,
        "test_fits_dir":test_fits_dir
        }
    
    if dataset_paths["dataset_dir"].exists():
        shutil.rmtree(dataset_paths["dataset_dir"])
    for key, val in dataset_paths.items():
        Path.mkdir(val,parents=True,exist_ok=False)
    if save_fits:
        for key, val in optional_dataset_paths.items():
            Path.mkdir(val,parents=True,exist_ok=False)
    
    other_paths = {"authentic_dataset_dir":authentic_dataset_dir,
                   "TRAIN_CNN":TRAIN_CNN_dir,
                   "tile_data_fits":tile_data_fits,
                   "psf_fits":psf_fits,
                   "dwarf_placement_mask_dir":dwarf_placement_mask_dir,
                   "outer_mask_npy":outer_mask_npy,
                   "total_mask_npy":total_mask_npy,
                    }
    
    paths = (dataset_paths | optional_dataset_paths | other_paths)
    
    return paths

def categorize_cutouts(num_cutouts,verbosity):
    num_dwarfs = num_cutouts/2
    num_nondwarfs = num_cutouts/2

    if num_dwarfs%1!=0:
        num_dwarfs = math.ceil(num_dwarfs)
    num_nondwarfs = num_cutouts - num_dwarfs

    train_frac, validate_frac, test_frac = 0.70, 0.15, 0.15

    num_dwarfs_train = num_dwarfs*train_frac
    num_dwarfs_validate = num_dwarfs*validate_frac
    num_dwarfs_test = num_dwarfs*test_frac
    num_nondwarfs_train = num_nondwarfs*train_frac
    num_nondwarfs_validate = num_nondwarfs*validate_frac
    num_nondwarfs_test = num_nondwarfs*test_frac

    if num_dwarfs_validate%1!=0:
        num_dwarfs_validate = math.ceil(num_dwarfs_validate)
    if num_dwarfs_test%1!=0:
        num_dwarfs_test = math.ceil(num_dwarfs_test)
    num_dwarfs_train = num_dwarfs - num_dwarfs_validate - num_dwarfs_test

    if num_nondwarfs_validate%1!=0:
        num_nondwarfs_validate = math.ceil(num_nondwarfs_validate)
    if num_nondwarfs_test%1!=0:
        num_nondwarfs_test = math.ceil(num_nondwarfs_test)
    num_nondwarfs_train = num_nondwarfs - num_nondwarfs_validate - num_nondwarfs_test

    ds_matrix = np.array([[num_dwarfs_train,num_dwarfs_validate,num_dwarfs_test,num_dwarfs],[num_nondwarfs_train,num_nondwarfs_validate,num_nondwarfs_test,num_nondwarfs]],dtype=int)
    
    if verbosity > 1:
        print(f"""
        number of dwarf cutouts: {ds_matrix[0,3]}
        number of nondwarf cutouts: {ds_matrix[1,3]}
        training, validation, test split: {train_frac}, {validate_frac}, {test_frac}

        number of dwarf cutouts used for training: {ds_matrix[0,0]}
        number of dwarf cutouts used for validation: {ds_matrix[0,1]}
        number of dwarf cutouts used for testing: {ds_matrix[0,2]}
        number of nondwarf cutouts used for training: {ds_matrix[1,0]}
        number of nondwarf cutouts used for validation: {ds_matrix[1,1]}
        number of nondwarf cutouts used for testing: {ds_matrix[1,2]}
        """)

    return ds_matrix

def create_authentic_cutouts(num_cutouts, tile, band, display=False, diagnostic=False, save_fits=False, verbosity=1):

    ds_matrix = categorize_cutouts(num_cutouts,verbosity)
    paths = configure_paths(tile,band,save_fits)

    if verbosity > 1:
        print("generating dwarf parameters...")

    '''trivial = False
    if difficulty == 'normal':
        mag, reff, n, q, theta = generate_parameters(ds_matrix[0,3], [-11, -6], None, None, display)
    elif difficulty == 'not_that_easy':
        mag, reff, n, q, theta = generate_parameters(ds_matrix[0,3], [-11, -8], 110, None, display)
    elif difficulty == 'easy':
        mag, reff, n, q, theta = generate_parameters(ds_matrix[0,3], [-11, -10], 110, None, display)
    elif difficulty == 'super_easy':
        mag, reff, n, q, theta = generate_parameters(ds_matrix[0,3], [-11,-10], 110, 20, display)
    elif difficulty == 'trivial':
        trivial = True'''
        
    mag, reff, n, q, theta = generate_parameters(ds_matrix[0,3], display=display)
    std_offset_pix = 15
    x_off = np.random.normal(0,std_offset_pix,ds_matrix[0,3])
    y_off = np.random.normal(0,std_offset_pix,ds_matrix[0,3])
    x0 = 256+x_off
    y0 = 256+y_off

    trivial = False

    with fits.open(paths["tile_data_fits"]) as hdul:
        data = hdul[0].data
    with fits.open(paths["psf_fits"]) as hdul:
        psf = hdul[0].data
        psf/=psf.sum()
    valid_dw_coords = np.load(paths["total_mask_npy"])
    valid_nd_coords = np.load(paths["outer_mask_npy"])

    make_cutouts(data,ds_matrix,paths,valid_dw_coords,valid_nd_coords,psf,mag,reff,n,q,theta,x0,y0,diagnostic,save_fits,trivial,verbosity)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('num_cutouts', type=int, help='Number of cutouts used to train the CNN.')
    parser.add_argument('tile', help="Tile to inject dwarfs into and create cutouts from.")
    parser.add_argument('band', help="Photometric band of the tile specified above.")
    #parser.add_argument('-difficulty', choices=['normal','not_that_easy','easy','super_easy','trivial'], default='normal', help='Specify the difficulty of the dataset. Useful for testing the CNN.')
    parser.add_argument('--verbosity', choices=[0,1,2], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')
    parser.add_argument('--display', action='store_true', default=False, help='Displays plots showing the distribution of dwarf parameters.')
    parser.add_argument('--diagnostic', action='store_true', default=False, help='Creates additional cutouts allowing one to check the dwarf insertion process. You must not use this option when creating the real dataset.')
    parser.add_argument('--save_fits', action='store_true', default=False, help='Produces the fits file versions of the jpegs, useful for inputting to the detection algorithm.')

    args = parser.parse_args()
    num_cutouts = args.num_cutouts
    tile = args.tile
    band = args.band
    #difficulty = args.difficulty
    verbosity = args.verbosity
    display = args.display
    diagnostic = args.diagnostic
    save_fits = args.save_fits

    create_authentic_cutouts(num_cutouts,tile,band,display=display,diagnostic=diagnostic,save_fits=save_fits,verbosity=verbosity)


'''
def get_dwarf_parameters(num_dwarfs):
    #these parameters (mag and reff) are normally and log-normally distributed and correlated
    mean_mag = 19.0
    std_mag = 1.0

    mean_log_radius = 3.4
    std_log_radius = 0.3

    correlation_coefficient = -0.7
    covariance_matrix = np.array([[std_mag**2, correlation_coefficient * std_mag * std_log_radius], [correlation_coefficient * std_mag * std_log_radius, std_log_radius**2]])

    normal_samples = multivariate_normal(mean=[mean_mag, mean_log_radius], cov=covariance_matrix, size=num_dwarfs)

    mag = normal_samples[:, 0]
    reff = np.exp(normal_samples[:, 1])

    #these parameters are uniformly distributed and not correlated
    n = np.random.uniform(0.35,2.15,num_dwarfs)
    q = np.random.uniform(0.5,0.95,num_dwarfs)
    theta = np.random.uniform(0,360,num_dwarfs)

    return mag, reff, n, q, theta
'''