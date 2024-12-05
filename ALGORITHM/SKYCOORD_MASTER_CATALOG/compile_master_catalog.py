import argparse
import pandas as pd
import warnings
import time
from datetime import datetime

def create_signature(data_in_file,signature):
    timestr = datetime.now().strftime("%Y%m%d%H%M%S")
    if signature is None:
        signature = f"{data_in_file.stem}_{timestr}"
    return signature

def compile_master_catalog(csv_dir,master_catalog_dir,signature=None,verbosity=1):
    t1 = time.perf_counter()
    if verbosity > 0:
        print(" Compiling master catalog of sky coordinates...")

    filtered_csvs = list(csv_dir.glob("*_filtered_detections.csv"))
    skycoords = pd.DataFrame(columns=['ALPHA_J2000','DELTA_J2000'])
    warnings.simplefilter(action='ignore', category=FutureWarning)
    for csv in filtered_csvs:
        df = pd.read_csv(csv)
        skycoords = pd.concat([skycoords,df[['ALPHA_J2000','DELTA_J2000']]],ignore_index=True)
    num_skycoords = len(skycoords)
    tolerance = 1e-3
    skycoords_unique = skycoords.loc[~((skycoords['ALPHA_J2000'].diff().abs() < tolerance) & (skycoords['DELTA_J2000'].diff().abs() < tolerance))]
    skycoords_duplicates = skycoords.loc[(skycoords['ALPHA_J2000'].diff().abs() < tolerance) & (skycoords['DELTA_J2000'].diff().abs() < tolerance)]
    num_unique_skycoords = len(skycoords_unique)
    if verbosity > 0:
        print(f"  Removed {num_skycoords - num_unique_skycoords} duplicate skycoords from catalog ({num_unique_skycoords} remaining)")
    skycoords_unique.to_csv(master_catalog_dir/f"{signature}_master_catalog.csv",index=False)
    skycoords_duplicates.to_csv(master_catalog_dir/f"{signature}_duplicates_catalog.csv",index=False)

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f" Finished compiling master catalog. Time taken: {t2-t1}")

