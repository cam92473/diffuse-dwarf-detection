import pandas as pd
import numpy as np
import argparse
import time
from pathlib import Path
pd.options.mode.chained_assignment = None  # default='warn'

def compare_catalogs(outdir,match_tol,signature,verbose):

    if verbose:
        print("comparing catalogs...")
        t1 = time.perf_counter()

    art = pd.read_csv(outdir/f'{signature}_input_artificial_dwarfs.csv')
    det = pd.read_csv(outdir/f'{signature}_filtered_detections.csv')

    artmatch_list = []
    #Iterate through the detections, finding out for each detection row if there is an artificial dwarf row corresponding to it (via position).
    #If so, attach the 'NUMBER' value of the detection row to the corresponding artificial dwarf row.
    #Then a table of artificial dwarf rows corresponding to detection rows is created, with the NUMBER column showing which rows correspond.
    #This table is merged with the original detection catalog to produce the match catalog.
    for i, row in det.iterrows():
        artmatch = art.loc[(art.x - row.X_IMAGE)**2 + (art.y - row.Y_IMAGE)**2 <= match_tol]
        artmatch['NUMBER'] = i+1
        artmatch_list.append(artmatch)
    artmatches = pd.concat(artmatch_list)

    matchcat = pd.merge(det, artmatches, on='NUMBER', how='left').dropna()
    matchcat = matchcat.iloc[:,15:]
    matchcat.to_csv(outdir/f'{signature}_detected_artificial_dwarfs.csv',index=False)

    nonmatchcat = pd.merge(det,artmatches, indicator=True, how='outer').query('_merge=="left_only"').drop('_merge', axis=1)
    nonmatchcat = nonmatchcat.iloc[:,:15]
    nonmatchcat.to_csv(outdir/f'{signature}_non_artificial_dwarf_detections.csv',index=False)

    if verbose:
        t2 = time.perf_counter()
        print(f"comparing catalogs time: {t2-t1}")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('outdir', help='Output folder containing the artificial and detection catalogs.')
    parser.add_argument('signature', help='The signature used to identify the files in the output folder.')
    parser.add_argument('-match_tol', type=float, default=2, help='The maximum squared distance, in pixels, a detected dwarf may be found from an inputted artificial dwarf for the program to consider it a match. Used to construct the match catalog.')
    parser.add_argument('--verbose', action='store_true', default=False, help='Displays messages in the terminal.')

    args = parser.parse_args()
    outdir = Path(args.outdir).resolve()
    signature = args.signature
    match_tol = args.match_tol
    verbose = args.verbose

    compare_catalogs(outdir,match_tol,signature,verbose)


