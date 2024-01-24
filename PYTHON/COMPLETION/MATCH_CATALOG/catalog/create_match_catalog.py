import pandas as pd
import numpy as np
import argparse
import time

def create_match_catalog(master_artificial_dwarfs_catalog,master_filtered_detections_catalog,match_catalog,tol,signature,verbose):

    if verbose:
        print("creating match catalog...")
        t1 = time.perf_counter()

    mart = pd.read_table(master_artificial_dwarfs_catalog,sep='\s+',escapechar='#')
    mdet = pd.read_table(master_filtered_detections_catalog,sep='\s+',escapechar='#')

    mart_list = []
    tol = 2
    mdet['merge_row'] = mdet.index.values  # Make a row to merge on with the index values
    for i, row in mdet.iterrows():
        mart_potmatch = mart.loc[(mart.x - row.X_IMAGE)**2 + (mart.y - row.Y_IMAGE)**2 <= tol]
        mart_potmatch['merge_row'] = i # Add a merge row
        mart_list.append(mart_potmatch)
    mart_found = pd.concat(mart_list)

    result = pd.merge(mdet, mart_found, on='merge_row', how='left').dropna()
    idx = result.columns.get_loc('merge_row')
    matchcat = result.iloc[:,idx+1:]
    matchcat.columns = ['x0','y0','gmag','Ieff_SB','I0_SB','reff','n','axisratio','theta','x','y']

    np.savetxt(match_catalog,matchcat,fmt=['%-20d','%-20d','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f'],header=f"{'x0':<20s}{'y0':<20s}{'gmag':<21s}{'Ieff_SB':<21s}{'I0_SB':<21s}{'reff':<21s}{'n':<21s}{'axisratio':<21s}{'theta':<21s}{'x':<21s}{'y':<21s}")

    if verbose:
        t2 = time.perf_counter()
        print(f"match catalog creation time: {t2-t1}")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('_catalog', help='Path of the input catalog.')
    parser.add_argument('filtered_detections', help='Path of the output catalog.')
    parser.add_argument('match', help='Path of the to-be-created match catalog.')

    args = parser.parse_args()
    artificial_dwarfs = args.artificial_dwarfs
    filtered_detections = args.filtered_detections
    match = args.match

    create_match_catalog(artificial_dwarfs,filtered_detections,match)


