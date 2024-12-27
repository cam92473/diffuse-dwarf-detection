import argparse
import time
from datetime import datetime
from pathlib import Path
import shutil
import csv
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

def cutout_detections(data,is_tile,paths,save,play_through,signature,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(f"  Making cutouts...")
    make_cutouts(data,is_tile,paths["master_catalog_dir"],paths["tile_color_gzu_jpeg"],paths["save_dir"],paths["cutouts_dir"],save=save,play_through=play_through,signature=signature,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"  Finished making cutouts. Total time: {t2-t1}")

def compile_master_catalog(data,is_tile,detection_mask,injected_coords,injected_params,known_dwarfs,paths,save,play_through,signature,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Compiling master catalog of detection coordinates...")
    get_master_catalog(data,is_tile,detection_mask,injected_coords,injected_params,known_dwarfs,paths['initial_completeness_csv'],paths['csv_dir'],paths["master_catalog_dir"],paths["tile_color_gzu_jpeg"],paths["save_dir"],save=save,play_through=play_through,signature=signature,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished compiling master catalog. Time taken: {t2-t1}") 

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

def image_process_chunks(paths,chunkinfo_json,medblur_radius,save,play_through,signature,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Image processing chunks with GIMP...")
    for i, preprocessed_data_chunk in enumerate(natsorted(list(paths["preprocessed_dir"].iterdir()))):
        if chunkinfo_json is None:
            signature_i = signature
            name = ""
        else:
            signature_i = f"{signature}_chunk{i+1}"
            name = f" chunk{i+1}"
        gimp_call(preprocessed_data_chunk,paths["processed_dir"]/f'{signature_i}_processed.fits',paths["save_dir"],paths["gimp_procedure_dir"],medblur_radius,name=name,save=save,play_through=play_through,signature=signature_i,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished image processing chunks. Total time: {t2-t1}")

def preprocess_chunks(paths,chunkinfo_json,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Preprocessing chunks...")
    for i, raw_data_chunk in enumerate(natsorted(list(paths["chunks_data_dir"].iterdir()))):
        if chunkinfo_json is None:
            name = ""
        else:
            name = f" chunk{i+1}"
        preprocess(raw_data_chunk,paths["preprocessed_dir"]/(raw_data_chunk.stem+"_gmp.fits"),name=name,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished preprocessing chunks. Total time: {t2-t1}")

def cutout_chunks(data,is_tile,chunkinfo_json,paths,save,play_through,signature,verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Chunking...")
    if chunkinfo_json is None:
        shutil.copy(data,paths["chunks_data_dir"]/f'{signature}.fits')
    else:
        chunk(data,paths["chunks_data_dir"],is_tile,chunkinfo_json,paths["tile_color_gzu_jpeg"],paths["save_dir"],save=save,play_through=play_through,signature=signature,verbosity=verbosity)
    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished chunking. Total time: {t2-t1}")

def configure_paths(data,is_tile,save,signature):
    algm_dir = (Path(__file__).parent).resolve()
    root_dir = algm_dir.parent
    ch_dir = algm_dir/'CHUNKS'
    chunks_data_dir = ch_dir/'chunks'/signature
    chunks_data_dir.mkdir(exist_ok=True,parents=True)
    if is_tile:
        tile_color_gzu_jpeg = next(data.parents[1].glob("*zgu_asinh.jpg"))
    else:
        tile_color_gzu_jpeg = None
    pp_dir = algm_dir/"PREPROCESS"
    preprocessed_dir = pp_dir/"preprocessed"/signature
    preprocessed_dir.mkdir(exist_ok=True,parents=True)
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
    mc_dir = algm_dir/'MASTER_CATALOG'
    master_catalog_dir = mc_dir/'master_catalog'/signature
    master_catalog_dir.mkdir(exist_ok=True,parents=True)
    initial_completeness_csv = master_catalog_dir/f'{signature}_initial_completeness.csv'
    if initial_completeness_csv.exists() == False:
        with open(initial_completeness_csv, mode='x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['mag', 'reff', 'n', 'q', 'theta', 'completeness'])
    co_dir = algm_dir/'CUTOUT'
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
             "ROOT":root_dir,
             "ALGORITHM":algm_dir,
             "CHUNKS":ch_dir,
             "chunks_data_dir": chunks_data_dir,
             "tile_color_gzu_jpeg":tile_color_gzu_jpeg,
             "PREPROCESS":pp_dir,
             "preprocessed_dir":preprocessed_dir,
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
             "MASTER_CATALOG":mc_dir,
             "master_catalog_dir":master_catalog_dir,
             "initial_completeness_csv":initial_completeness_csv
            }

    return paths

def create_signature(data,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        #signature = f"{tile}_{band}_{timestr}"
        signature = f"{data.stem}_{timestr}"
    return signature

def detect_dwarfs(data, chunkinfo_json, medblur_radius, detect_params, detection_mask, injected_coords, injected_params, known_dwarfs, is_tile=False, save=False, play_through=False, signature=None, verbosity=1):

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

    if not isinstance(data,Path):
        data = Path(data).resolve()
    if chunkinfo_json is not None:
        if not isinstance(chunkinfo_json,Path):
            chunkinfo_json = Path(chunkinfo_json).resolve()
    if detection_mask is not None:
        if not isinstance(detection_mask,Path):
            detection_mask = Path(detection_mask).resolve()
    if known_dwarfs is not None:
        if not isinstance(known_dwarfs,Path):
            known_dwarfs = Path(known_dwarfs).resolve()

    t_start = time.perf_counter()
    if verbosity > 0:
        print("Starting algorithm...")

    signature = create_signature(data,signature)
    paths = configure_paths(data,is_tile,save,signature)
    
    cutout_chunks(data,is_tile,chunkinfo_json,paths,save,play_through,signature,verbosity)
    preprocess_chunks(paths,chunkinfo_json,verbosity)
    image_process_chunks(paths,chunkinfo_json,medblur_radius,save,play_through,signature,verbosity)
    detect_filter_chunks(paths,detect_params,save,play_through,signature,verbosity)
    compile_master_catalog(data,is_tile,detection_mask,injected_coords,injected_params,known_dwarfs,paths,save,play_through,signature,verbosity)
    cutout_detections(data,is_tile,paths,save,play_through,signature,verbosity)
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

    from CHUNKS.chunk import chunk
    from PREPROCESS.preprocess import preprocess
    from IMAGE_PROCESS.gimp_call import gimp_call
    from DETECT_FILTER.detect_filter import detect_filter
    from MASTER_CATALOG.get_master_catalog import get_master_catalog
    from CUTOUT.make_cutouts import make_cutouts

    parser = argparse.ArgumentParser(description='Dwarf detection algorithm')
    parser.add_argument('data', help="The science image you want to discover dwarfs in.")
    parser.add_argument('-chunkinfo_json', help='Path to the json file containing info on how to chunk the image. If no file is supplied, the image will not be chunked.')
    parser.add_argument('-medblur_radius', type=int, default=30, help='Radius of the circular kernel used by Gimp to median filter the image.')
    parser.add_argument('-detect_params', nargs=2, type=int, default=[500,3], help='The DETECT_MINAREA and DETECT_THRESH sextractor parameters used to detect objects in the median-filtered image.')
    parser.add_argument('-detection_mask', help='Mask for the entire image (not an individual chunk) that is True for pixels where a detection is allowed (a cutout can be made), typically a distance of 256 (the cutout radius) or further from the edge of the image or a NaN region. The algorithm can construct this on its own, but you can supply it to speed up the algorithm if the input image is large.')
    parser.add_argument('-injected_coords', help='(x,y) coordinates of the injected dwarf galaxies, if applicable. Supplying these will cause the algorithm to exit before the CNN stage and distribute detection cutouts into two folders (dwarfs and non-dwarfs), supplying training data for the CNN.')
    parser.add_argument('-injected_params', help='Parameters of the injected dwarf galaxies.')
    parser.add_argument('-known_dwarfs', help='CSV containing coordinates of known dwarf galaxies. Used only when generating training data for the CNN.')
    parser.add_argument('--is-tile', action='store_true', default=False, help='Use this flag to indicate that the data file is the whole tile, allowing some speedups to be made when generating JPEGs.')
    parser.add_argument('--save', action='store_true', default=False, help='Saves jpegs showing various stages of the algorithm operating on the image. These jpegs are saved to a single folder.')
    parser.add_argument('--play_through', action='store_true', default=False, help='Executes the algorithm in play-through mode, allowing you to observe the algorithm working in "real time" (through the Gimp UI). Do not use if the image is very big or a huge slowdown will occur.')
    parser.add_argument('--signature', help='Name used to identify the files of this run. If not specified, a name will be created based on the input data name and the current time.')
    parser.add_argument('--verbosity', choices=[0,1,2], default=1, help='Controls the volume of messages displayed in the terminal. 0=silent, 1=normal, 2=diagnostic.')

    args = parser.parse_args()
    data = Path(args.data).resolve()
    chunkinfo_json = Path(args.chunkinfo_json).resolve()
    medblur_radius = args.medblur_radius
    detect_params = args.detect_params
    detection_mask = args.detection_mask
    injected_coords = args.injected_coords
    injected_params = args.injected_params
    known_dwarfs = Path(args.known_dwarfs).resolve()
    is_tile = args.is_tile
    save = args.save
    play_through = args.play_through
    signature = args.signature
    verbosity = args.verbosity

    detect_dwarfs(data, chunkinfo_json, medblur_radius, detect_params, detection_mask, injected_coords, injected_params, known_dwarfs, is_tile=is_tile, save=save, play_through=play_through, signature=signature, verbosity=verbosity)

else:

    from ALGORITHM.CHUNKS.chunk import chunk
    from ALGORITHM.PREPROCESS.preprocess import preprocess
    from ALGORITHM.IMAGE_PROCESS.gimp_call import gimp_call
    from ALGORITHM.DETECT_FILTER.detect_filter import detect_filter
    from ALGORITHM.MASTER_CATALOG.get_master_catalog import get_master_catalog
    from ALGORITHM.CUTOUT.make_cutouts import make_cutouts