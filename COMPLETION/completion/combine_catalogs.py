import argparse
import time

def combine_catalogs(parent, num_runs, verbose):  
    
    if verbose:
        print("combining catalogs of individual runs...")
        t1 = time.perf_counter()

    input_catalogues = [parent/f'{parent.name}-{i}'/'artificial_dwarfs.catalog' for i in range(num_runs)]
    match_catalogues = [parent/f'{parent.name}-{i}'/'matches.catalog' for i in range(num_runs)]

    start = 0
    with open(parent/'all_artificial_dwarfs.catalogue','w') as outcat:
        for cat in input_catalogues:
            with open(cat,'r') as incat:
                outcat.writelines(incat.readlines()[start:])
            start = 1
    start = 0
    with open(parent/'all_matches.catalogue','w') as outcat:
        for cat in match_catalogues:
            with open(cat,'r') as incat:
                outcat.writelines(incat.readlines()[start:])
            start = 1
    
    if verbose:
        t2 = time.perf_counter()
        print(f"combining time: {t2-t1}")
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('tileno', type=str, help='Tile to create combined catalogue for. Include the word "tile", i.e., "tile4"')
    parser.add_argument('numcats', type=int, help='Number of catalogues to combine.')

    args = parser.parse_args()
    tileno = args.tileno
    numcats = args.numcats

    combine_catalogs(tileno,numcats)