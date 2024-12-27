import argparse
import shutil
from pathlib import Path

def get_purgeable_paths(signature,no_cutout):
    algm_dir = (Path(__file__).parent).resolve()
    ch_dir = algm_dir/'CHUNKS'
    chunks_data_dir = ch_dir/'chunks'/signature
    pp_dir = algm_dir/"PREPROCESS"
    preprocessed_dir = pp_dir/"preprocessed"/signature
    ip_dir = algm_dir/'IMAGE_PROCESS'
    processed_dir = ip_dir/'processed'/signature
    df_dir = algm_dir/'DETECT_FILTER'
    csv_dir = df_dir/'csv'/signature
    segmap_dir = df_dir/'segmap'/signature
    mc_dir = algm_dir/'MASTER_CATALOG'
    master_catalog_dir = mc_dir/'master_catalog'/signature
    co_dir = algm_dir/'CUTOUT'
    cutouts_dir = co_dir/'cutouts'/signature
    sr_dir = algm_dir/'saved_runs'
    save_dir = sr_dir/signature

    if no_cutout:
        purgeable_paths = {
                "chunks_data_dir": chunks_data_dir,
                "preprocessed_dir":preprocessed_dir,
                "processed_dir":processed_dir,
                "save_dir":save_dir,
                "csv_dir":csv_dir,
                "segmap_dir":segmap_dir,
                "master_catalog_dir":master_catalog_dir,
                }
    else:
        purgeable_paths = {
                "chunks_data_dir": chunks_data_dir,
                "preprocessed_dir":preprocessed_dir,
                "processed_dir":processed_dir,
                "save_dir":save_dir,
                "csv_dir":csv_dir,
                "segmap_dir":segmap_dir,
                "master_catalog_dir":master_catalog_dir,
                "cutouts_dir":cutouts_dir,
        }
                        
    for key in purgeable_paths:
        purgeable_paths[key] = Path(purgeable_paths[key]).resolve()

    return purgeable_paths

def purge(signature,no_cutout):

    purgeable_paths = get_purgeable_paths(signature,no_cutout)
    to_delete = []
    for _, folder in purgeable_paths.items():
        if folder.exists():
            to_delete.append(folder)

    algm_dir = (Path(__file__).parent).resolve()
    to_delete_readable = [str(i.relative_to(algm_dir)) for i in to_delete]

    while True:
        response = input(f"The following folders are marked for deletion: {to_delete_readable}. Confirm deletion? (y/n): ").strip().lower()
        if response == 'y':
            for folder in to_delete:
                shutil.rmtree(folder)
            print("done")
            break
        elif response == 'n':
            print("cancelled")
            break
        else:
            print("invalid input")
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Removes files associated with a provided signature from the ALGORITHM directory, freeing space.')
    parser.add_argument('signature', help='Signature you wish to purge.')
    parser.add_argument('--no-cutout', action='store_true', default=False, help='Toggle if you wish to make an exception for the CUTOUT directory of the specified signature.')
    args = parser.parse_args()
    
    purge(args.signature,args.no_cutout)