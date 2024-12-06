import argparse
import time
from datetime import datetime
from pathlib import Path
import shutil
from astropy.io import fits
from astropy.wcs import WCS
from natsort import natsorted

'''def create_sigfolder(data,supplied_signature,timestr):
    if supplied_signature is None:
        if data.is_dir():
            sigfolder = data.parents[2].stem+"_"+data.parents[1].stem+"_"+data.parents[0].stem+"_"+timestr
    else:
        sigfolder = supplied_signature
    return sigfolder'''

'''
"CONSULT_CNN":cnn_dir,
"cnn_results_dir":cnnres_dir,
"dwarf_dir":dwarf_dir,
"nondwarf_dir":nondwarf_dir,

}'''



def cleanup_folders(paths):
    for dir in [paths["processed_dir"],paths["csv_dir"],paths["segmap_dir"],paths["cutouts_dir"],paths["cnn_results_dir"]]:
        shutil.rmtree(dir)

def make_color_cutouts(paths,save,signature,verbosity):
    band_names = ["g"]
    band_files = [paths["tile_dir"]/"g"/f"{tile}cut_g.fits"] #paths["tile_dir"]/"r"/f"{tile}cut_r.fits",paths["tile_dir"]/"i"/f"{tile}cut_i.fits",paths["tile_dir"]/"z"/f"{tile}cut_z.fits"
    with fits.open(paths["tile_dir"]/"i"/f"{tile}cut_i.fits") as hdul:
        i_wcs = WCS(hdul[0].header)
    make_cutouts(paths["master_catalog_dir"],band_files,band_names,paths["tile_color_gzu_jpeg"],paths["save_dir"]/f'{signature}_K_cutout_locations.jpg',i_wcs,paths["cutouts_dir"],save=save,signature=signature,verbosity=verbosity)

def detect_filter_chunks(paths,detect_params,save,play_through,signature,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Detecting and filtering diffuse objects with Source Extractor...")
    for i, processed_chunk in enumerate(natsorted(list(paths["processed_dir"].iterdir()))):
        signature_i = f"{signature}_chunk{i+1}"
        detect_filter(processed_chunk,paths['segmap_dir'],paths['csv_dir'],paths["sextractor_dir"],paths["save_dir"],detect_params,name=f" chunk{i+1}",save=save,play_through=play_through,signature=signature_i,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished detecting and filtering diffuse objects. Total time: {t2-t1}")

def image_process_chunks(paths,medblur_radius,save,play_through,signature,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Image processing chunks with GIMP...")
    for i, (preprocessed_data_chunk, preprocessed_weight_chunk) in enumerate(zip(natsorted(list(paths["gimpready_dir"].iterdir())),natsorted(list(paths["weight_dir"].iterdir())))):
        signature_i = f"{signature}_chunk{i+1}"
        gimp_call(preprocessed_data_chunk,preprocessed_weight_chunk,paths["processed_dir"]/f'{signature_i}_processed.fits',paths["save_dir"],paths["gimp_procedure_dir"],medblur_radius,name=f" chunk{i+1}",save=save,play_through=play_through,signature=signature_i,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished image processing chunks. Total time: {t2-t1}")

def preprocess_chunks(paths,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Preprocessing chunks...")
    for i, (raw_data_chunk, raw_weight_chunk) in enumerate(zip(natsorted(list(paths["chunks_data_dir"].iterdir())),natsorted(list(paths["chunks_weight_dir"].iterdir())))):
        preprocess(raw_data_chunk,raw_weight_chunk,paths["gimpready_dir"]/(raw_data_chunk.stem+"_gmp.fits"),paths["weight_dir"]/raw_weight_chunk.name,name=f" chunk{i+1}",verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished preprocessing chunks. Total time: {t2-t1}")

def configure_paths(save,signature):
    tile = 'tile4'
    algm_dir = (Path(__file__).parent).resolve()
    root_dir = algm_dir.parent
    inputimages_dir = root_dir/'input_images'
    tile_dir = inputimages_dir/'tiles'/tile
    #tile_data_fits = tile_dir/band/f"{tile}cut_{band}.fits"
    #tile_weight_fits = tile_dir/band/f"{tile}cut_{band}_weight.fits" 
    ch_dir = algm_dir/'CHUNKS'
    chunks_data_dir = ch_dir/'chunks'/signature/'data'
    chunks_data_dir.mkdir(exist_ok=True,parents=True)
    chunks_weight_dir = ch_dir/'chunks'/signature/'weight'
    chunks_weight_dir.mkdir(exist_ok=True,parents=True)
    tile_color_gzu_jpeg = tile_dir/f"{tile}_zgu_asinh.jpg"
    pp_dir = algm_dir/"PREPROCESS"
    preprocessed_dir = pp_dir/"preprocessed"
    gimpready_dir = preprocessed_dir/signature/"gimp_ready"
    gimpready_dir.mkdir(exist_ok=True,parents=True)
    weight_dir = preprocessed_dir/signature/"weight"
    weight_dir.mkdir(exist_ok=True,parents=True)
    ip_dir = algm_dir/'IMAGE_PROCESS'
    processed_dir = ip_dir/'processed'/signature
    processed_dir.mkdir(exist_ok=True,parents=True)
    gimpproc_dir = ip_dir/'gimp_procedure'
    df_dir = algm_dir/'DETECT_FILTER'
    sextr_dir = df_dir/'sextractor'
    csv_dir = df_dir/'csv'/signature
    csv_dir.mkdir(exist_ok=True,parents=True)
    segmap_dir = df_dir/'segmap'/signature
    segmap_dir.mkdir(exist_ok=True,parents=True)
    smc_dir = algm_dir/'SKYCOORD_MASTER_CATALOG'
    master_catalog_dir = smc_dir/'master_catalogs'/signature
    master_catalog_dir.mkdir(exist_ok=True,parents=True)
    co_dir = algm_dir/'CUTOUT_COLOR'
    cutouts_dir = co_dir/'cutouts'/signature
    cutouts_dir.mkdir(exist_ok=True,parents=True)
    #cnn_dir = algm_dir/'CONSULT_CNN'
    #cnnres_dir = cnn_dir/'CNN_results'/signature
    #dwarf_dir = cnnres_dir/'dwarf'
    #dwarf_dir.mkdir(exist_ok=True,parents=True)
    #nondwarf_dir = cnnres_dir/'nondwarf'
    #nondwarf_dir.mkdir(exist_ok=True,parents=True)
    sr_dir = algm_dir/'saved_runs'
    save_dir = sr_dir/signature
    if save:
        save_dir.mkdir(exist_ok=True,parents=True)

    #"tile_data_fits":tile_data_fits,
    #"tile_weight_fits":tile_weight_fits,

    paths = {
             "tile_dir":tile_dir,
             "ROOT":root_dir,
             "ALGORITHM":algm_dir,
             "CHUNKS":ch_dir,
             "chunks_data_dir": chunks_data_dir,
             "chunks_weight_dir":chunks_weight_dir,
             "tile_color_gzu_jpeg":tile_color_gzu_jpeg,
             "PREPROCESS":pp_dir,
             "preprocessed":preprocessed_dir,
             "gimpready_dir":gimpready_dir,
             "weight_dir":weight_dir,
             "IMAGE_PROCESS":ip_dir,
             "processed_dir":processed_dir,
             "gimp_procedure_dir":gimpproc_dir,
             "saved_runs_dir":sr_dir,
             "save_dir":save_dir,
             "DETECT_FILTER":df_dir,
             "sextractor_dir":sextr_dir,
             "csv_dir":csv_dir,
             "segmap_dir":segmap_dir,
             "cutouts_dir":cutouts_dir,
             "SKYCOORD_MASTER_CATALOG":smc_dir,
             "master_catalog_dir":master_catalog_dir,
            }

    return paths

def create_signature(data,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        #signature = f"{tile}_{band}_{timestr}"
        signature = f"{data.stem}_{timestr}"
    return signature

def detect_dwarfs(data, weight, medblur_radius, detect_params, save=False, dirty=False, play_through=False, signature=None, verbosity=1):

    #input from command line or GUI (among them, pick a filter to get the DCM in)
    #in this filter:
    #split into chunks
    #preprocess
    #image process
    #detect and filter
    #extract unique skycoords
    #now make cutouts from original image in specified colors
    #pass cutouts to CNN
    #human verification
    #display results


    t_start = time.perf_counter()
    if verbosity > 0:
        print("Starting algorithm...")

    signature = create_signature(data,signature)
    paths = configure_paths(save,signature)

    cutout_chunks(data,weight,paths["chunks_data_dir"],paths["chunks_weight_dir"],paths["tile_color_gzu_jpeg"],paths["save_dir"]/f'{signature}_A_chunks.jpg',save=save,signature=signature,verbosity=verbosity)
    preprocess_chunks(paths,verbosity)
    image_process_chunks(paths,medblur_radius,save,play_through,signature,verbosity)
    detect_filter_chunks(paths,detect_params,save,play_through,signature,verbosity)
    compile_master_catalog(paths["csv_dir"],paths["master_catalog_dir"],signature=signature,verbosity=verbosity)
    #make_color_cutouts(paths,save,signature,verbosity)
    #CNN

    '''if data.is_file() & weight.is_file():
        gimp_call(data, weight, medblur_radius, paths, save, play_through, signature, verbosity)
        detect_filter(paths["processed_dir"], paths, detect_params, save, play_through, signature, verbosity)
    elif data.is_dir() & weight.is_dir():
        sigfolder = create_sigfolder(data,supplied_signature,timestr)
        for i, (data_piece, weight_piece) in enumerate(zip(natsorted(list(data.iterdir())),natsorted(list(weight.iterdir())))):
            signature = create_signature(data_piece,supplied_signature,timestr,suffix=str(i+1))
            paths = configure_paths(data_piece,weight_piece,save,sigfolder+"/"+signature)
            gimp_call(data_piece, weight_piece, medblur_radius, paths, save, play_through, signature, verbosity)
            detect_filter(paths["processed_dir"], paths, detect_params, save, play_through, signature, verbosity)'''

    #make_cutouts(paths,)
    #consult_CNN(paths, verbosity)

    '''if not dirty:
        cleanup_folders(paths)'''

    t_end = time.perf_counter()
    if verbosity > 0:
        print(f"Finished algorithm, total time: {t_end-t_start}")

if __name__ == '__main__':

    from CHUNKS.cutout_chunks import cutout_chunks
    from PREPROCESS.preprocess import preprocess
    from IMAGE_PROCESS.gimp_call import gimp_call
    from DETECT_FILTER.detect_filter import detect_filter
    from SKYCOORD_MASTER_CATALOG.compile_master_catalog import compile_master_catalog
    from CUTOUT_COLOR.make_cutouts import make_cutouts

    parser = argparse.ArgumentParser(description='Dwarf detection algorithm')
    #parser.add_argument('tile', help='Tile you wish to analyze for dwarfs, e.g., "tile4".')
    #parser.add_argument('-dom_band', default='g', choices=['g','r','i','z'], help='The photometric band used to create the diffuse objects map, e.g., "g".')
    parser.add_argument('data')
    parser.add_argument('weight')
    parser.add_argument('-medblur_radius', type=int, default=30, help='Radius of the circular kernel used by Gimp to median filter the image.')
    parser.add_argument('-detect_params', nargs=2, type=int, default=[500,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the median-filtered image.')
    parser.add_argument('--save', action='store_true', default=False, help='Saves jpegs showing various stages of the algorithm operating on the image. These jpegs are saved to a single folder.')
    parser.add_argument('--dirty', action='store_true', default=False, help='If toggled, automatic cleaning of the directories after the algorithm has finished will not be done.')
    parser.add_argument('--play_through', action='store_true', default=False, help='Executes the algorithm in play-through mode, allowing you to observe the algorithm working in "real time" (through the Gimp UI). Do not use if the image is very big or a huge slowdown will occur.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=[0,1,2], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    #tile = args.tile
    #dom_band = args.dom_band
    data = Path(args.data).resolve()
    weight = Path(args.weight).resolve()
    medblur_radius = args.medblur_radius
    detect_params = args.detect_params
    save = args.save
    dirty = args.dirty
    play_through = args.play_through
    signature = args.signature
    verbosity = args.verbosity

    detect_dwarfs(data, weight, medblur_radius, detect_params, save=save, dirty=dirty, play_through=play_through, signature=signature, verbosity=verbosity)

else:

    from ALGORITHM.CHUNKS.cutout_chunks import cutout_chunks
    from ALGORITHM.PREPROCESS.preprocess import preprocess
    from ALGORITHM.IMAGE_PROCESS.gimp_call import gimp_call
    from ALGORITHM.DETECT_FILTER.detect_filter import detect_filter
    from ALGORITHM.SKYCOORD_MASTER_CATALOG.compile_master_catalog import compile_master_catalog
    #from ALGORITHM.CUTOUT_COLOR.make_cutouts import make_cutouts