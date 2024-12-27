import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from astropy.io import fits
import argparse
import shutil
from datetime import datetime
from pathlib import Path

def print_progress_bar (iteration, total, prefix = ''):
    percent = 100 * (iteration / float(total))
    length = 40
    filledLength = int(length * iteration // total)
    bar = '█' * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent:.0f}% complete', end = '\r')
    if iteration == total: 
        print("\n")

def generate_plots(mag,reff,n,q,theta,completeness,timestr,signature):
    df = pd.DataFrame(data={'apparent magnitude':mag,'effective radius':reff,'sersic index':n,'axis ratio':q,'position angle':theta,'completeness':completeness})
    norm = plt.Normalize(0, 1)
    g = sns.PairGrid(df, vars=["apparent magnitude", "effective radius", "sersic index", "axis ratio", "position angle"])
    g.map_offdiag(sns.scatterplot, hue=df["completeness"], palette="viridis", hue_norm=norm)
    g.map_diag(sns.histplot, color="gray", kde=False)
    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    sm.set_array([])
    g.fig.colorbar(sm, ax=g.axes, orientation="vertical", label="completeness")
    plt.savefig(f'COMPLETENESS/{signature}_initial_completeness_pairplot_{timestr}.png')
    plt.show()

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=df,
        y="apparent magnitude",
        x="effective radius",
        hue="completeness",
        palette="viridis",
        ax=ax,
        legend=False,
        s=100,
        alpha=0.8,
        hue_norm=norm
    )

    sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, orientation="vertical", label="completeness")
    ax.set_ylabel("apparent magnitude")
    ax.set_xlabel("effective radius")
    plt.savefig(f'COMPLETENESS/{signature}_initial_completeness_magreff_{timestr}.png')
    plt.show()

def inject_dwarfs(data,psf,num_injected_dwarfs,valid_dw_coords,mag_i,reff_i,n_i,q_i,theta_i):
    injected_coords = np.zeros((num_injected_dwarfs,2))
    j = 0
    while j < num_injected_dwarfs:
        x, y = np.random.randint(0,data.shape[1]), np.random.randint(0,data.shape[0])
        if valid_dw_coords[y,x]:
            injected_coords[j] = [x,y]
            valid_dw_coords[int(y-3*reff_i):int(y+3*reff_i),int(x-3*reff_i):int(x+3*reff_i)] = False
            data = insert_dwarf_intoarray(data,psf,mag_i,reff_i,n_i,q_i,theta_i,x,y,return_Ieff=False)
            print_progress_bar(j,num_injected_dwarfs-1,prefix=f'Dwarf {j+1}/{num_injected_dwarfs}')
            j += 1
            
    return data, injected_coords

def main(data_file,num_trials,num_injected_dwarfs,dwarf_parameters,chunkinfo_json,medblur_rad,detect_params,detection_mask,known_dwarfs,generate_training_data=False,is_tile=False,save=False,play_through=False,signature=None,verbosity=1):

    if dwarf_parameters is None:
        if verbosity > 0:
            print(f"Sampling {num_trials} points in parameter space...")
        mag, reff, n, q, theta = generate_parameters(num_dwarfs=num_trials,display=play_through)
    else:
        if verbosity > 0:
            print(f"Using supplied dwarf parameters...")
        mag, reff, n, q, theta = [0], [0], [0], [0], [0]
        mag[0], reff[0], n[0], q[0], theta[0] = [float(x) for x in dwarf_parameters]

    with fits.open('artificial_dwarf/psf/t4_dw2_g_psf.fits') as hdul:
        psf = hdul[0].data

    for i in range(num_trials):
        if verbosity > 0:
            print(f"Getting completeness for point {i} (mag {mag[i]:.1f}, reff {reff[i]:.1f}, n {n[i]:.1f}, q {q[i]:.1f}, theta {theta[i]:.1f})...")

        with fits.open(data_file) as hdul:
            data = hdul[0].data
            header = hdul[0].header

        if generate_training_data:
            valid_dw_coords = np.load(data_file.parent/(data_file.stem+'_dwarfplacementmask_ideal.npy'))
        else:
            valid_dw_coords = ~np.isnan(data)

        data, injected_coords = inject_dwarfs(data,psf,num_injected_dwarfs,valid_dw_coords,mag[i],reff[i],n[i],q[i],theta[i])
        
        injected_file = data_file.parent/(data_file.stem+'_injected'+data_file.suffix)
        fits.writeto(injected_file,data,header,overwrite=True)
        
        injected_params = np.array([mag[i],reff[i],n[i],q[i],theta[i]])
        detect_dwarfs(injected_file, chunkinfo_json, medblur_rad, detect_params, detection_mask, injected_coords, injected_params, known_dwarfs, is_tile=is_tile, save=save, play_through=play_through, signature=signature, verbosity=verbosity)

    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.move(f'ALGORITHM/MASTER_CATALOG/master_catalog/{signature}/{signature}_initial_completeness.csv',f'COMPLETENESS/{signature}_initial_completeness_{timestr}.csv')
    ic = pd.read_csv(f'COMPLETENESS/{signature}_initial_completeness_{timestr}.csv')
    completeness = ic['completeness']

    generate_plots(mag,reff,n,q,theta,completeness,timestr,signature)

if __name__ == '__main__':

    from ALGORITHM.algorithm import detect_dwarfs
    from artificial_dwarf.generate_parameters.generate_parameters import generate_parameters
    from artificial_dwarf.insert_dwarf import insert_dwarf_intoarray

    parser = argparse.ArgumentParser(description='Get completeness of the algorithm or generate training data for the CNN.')
    parser.add_argument('data_file', help="Path to the original science image.")
    parser.add_argument('num_trials', type=int, help="The number of points in parameter space you wish to sample.")
    parser.add_argument('num_injected_dwarfs', type=int, help="The number of dwarfs per sampled point you wish to inject into the image.")
    parser.add_argument('-dwarf_parameters', nargs=5, help='Optionally, you can supply the dwarf parameters of a single type of dwarf you want to inject; only useful for num_trials=1.')
    parser.add_argument('-chunkinfo_json', help='Path to the json file containing info on how to chunk the image. If no file is supplied, the image will not be chunked.')
    parser.add_argument('-medblur_radius', type=int, default=30, help='Radius of the circular kernel used by Gimp to median filter the image.')
    parser.add_argument('-detect_params', nargs=2, type=int, default=[500,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the median-filtered image.')
    parser.add_argument('-detection_mask', help='Mask for the entire image (not an individual chunk) that is True for pixels where a detection is allowed (a cutout can be made), typically a distance of 256 (the cutout radius) or further from the edge of the image or a NaN region. The algorithm can construct this on its own, but you can supply it to speed up the algorithm if the input image is large.')
    parser.add_argument('-known_dwarfs', help='CSV containing coordinates of known dwarf galaxies. Used only when generating training data for the CNN.')
    parser.add_argument('--generate-training-data', action='store_true', default=False, help='Exits the algorithm before the CNN, sorting cutouts into dwarf and nondwarf detections. These cutouts can be used to train the CNN.')
    parser.add_argument('--is-tile', action='store_true', default=False, help='Use this flag to indicate that the data file is the whole tile, allowing some speedups to be made when generating JPEGs.')
    parser.add_argument('--save', action='store_true', default=False, help='Saves jpegs showing various stages of the algorithm operating on the image. These jpegs are saved to a single folder.')
    parser.add_argument('--play_through', action='store_true', default=False, help='Executes the algorithm in play-through mode, allowing you to observe the algorithm working in "real time" (through the Gimp UI). Do not use if the image is very big or a huge slowdown will occur.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=[0,1,2], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data_file = Path(args.data_file).resolve()
    num_trials = args.num_trials
    num_injected_dwarfs = args.num_injected_dwarfs
    dwarf_parameters = args.dwarf_parameters
    chunkinfo_json = Path(args.chunkinfo_json).resolve()
    medblur_radius = args.medblur_radius
    detect_params = args.detect_params
    detection_mask = Path(args.detection_mask).resolve()
    known_dwarfs = Path(args.known_dwarfs).resolve()
    generate_training_data = args.generate_training_data
    is_tile = args.is_tile
    save = args.save
    play_through = args.play_through
    signature = args.signature
    verbosity = args.verbosity

    main(data_file, num_trials, num_injected_dwarfs, dwarf_parameters, chunkinfo_json, medblur_radius, detect_params, detection_mask, known_dwarfs, generate_training_data=generate_training_data, is_tile=is_tile, save=save, play_through=play_through, signature=signature, verbosity=verbosity)

