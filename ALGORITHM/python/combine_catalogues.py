import argparse
from pathlib import Path

def combine_catalogues(parent_path, num_runs):

    parent_path = Path(parent_path)    

    input_catalogues = [parent_path/f'{parent_path.name}_{i}'/'input.catalog' for i in range(num_runs)]
    match_catalogues = [parent_path/f'{parent_path.name}_{i}'/'match.catalog' for i in range(num_runs)]

    start = 0
    with open(parent_path/'tile4_allinput.catalogue','w') as outcat:
        for cat in input_catalogues:
            with open(cat,'r') as incat:
                outcat.writelines(incat.readlines()[start:])
            start = 1
    start = 0
    with open(parent_path/'tile4_allmatch.catalogue','w') as outcat:
        for cat in match_catalogues:
            with open(cat,'r') as incat:
                outcat.writelines(incat.readlines()[start:])
            start = 1
    print("done")
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('tileno', type=str, help='Tile to create combined catalogue for. Include the word "tile", i.e., "tile4"')
    parser.add_argument('numcats', type=int, help='Number of catalogues to combine.')

    args = parser.parse_args()
    tileno = args.tileno
    numcats = args.numcats

    combine_catalogues(tileno,numcats)