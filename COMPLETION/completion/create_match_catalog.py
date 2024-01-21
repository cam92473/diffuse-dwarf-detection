import pandas as pd
import numpy as np
import argparse
import time

def create_match_catalog(artificial_dwarfs,filtered_detections,matches,verbose):

    if verbose:
        print("creating match catalog...")
        t1 = time.perf_counter()

    inputcat = pd.read_table(artificial_dwarfs,sep='\s+',escapechar='#')
    alldetectionscat = pd.read_table(filtered_detections,sep='\s+',escapechar='#')

    df2 = inputcat
    df1 = alldetectionscat

    df2_list = []
    df1['merge_row'] = df1.index.values  # Make a row to merge on with the index values
    for i, row in df1.iterrows():
        df2_subset = df2.loc[(df2.x - row.X_IMAGE)**2 + (df2.y - row.Y_IMAGE)**2 <= 2]
        df2_subset['merge_row'] = i # Add a merge row
        df2_list.append(df2_subset)
    df2_found = pd.concat(df2_list)

    result = pd.merge(df1, df2_found, on='merge_row', how='left').dropna()
    idx = result.columns.get_loc('merge_row')
    matchcat = result.iloc[:,idx+1:]
    matchcat.columns = ['x0','y0','gmag','Ieff_SB','I0_SB','reff','n','axisratio','theta','x','y']

    np.savetxt(matches,matchcat,fmt=['%-20d','%-20d','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f','%-20.5f'],header=f"{'x0':<20s}{'y0':<20s}{'gmag':<21s}{'Ieff_SB':<21s}{'I0_SB':<21s}{'reff':<21s}{'n':<21s}{'axisratio':<21s}{'theta':<21s}{'x':<21s}{'y':<21s}")

    if verbose:
        t2 = time.perf_counter()
        print(f"match catalog creation time: {t2-t1}")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('artificial_dwarfs', help='Path of the input catalog.')
    parser.add_argument('filtered_detections', help='Path of the output catalog.')
    parser.add_argument('match', help='Path of the to-be-created match catalog.')

    args = parser.parse_args()
    artificial_dwarfs = args.artificial_dwarfs
    filtered_detections = args.filtered_detections
    match = args.match

    create_match_catalog(artificial_dwarfs,filtered_detections,match)


