from astropy.io import fits
import numpy as np
import argparse
from pathlib import Path

def cut_tiles(tiles,bands):

    if ('[' in tiles) and (']' in tiles):
        tile_list = tiles[1:-1].split(',')
    else:
        tile_list = [tiles]

    if ('[' in bands) and (']' in bands):
        band_list = bands[1:-1].split(',')
    else:
        band_list = [bands]

    for tile in tile_list:
        for band in band_list:
            with fits.open(Path.cwd()/tile/band/f"survey_{tile}_{band}_short_ALIGNi.fits") as hdul:
                data = hdul[0].data
                hdr = hdul[0].header
            with fits.open(Path.cwd()/tile/band/f"survey_{tile}_{band}_short_ALIGNi.WEIGHT.fits") as hdul:
                weight = hdul[0].data

            nanmask = np.load('nanmask.npy')
            data[nanmask] = np.nan
            weight[nanmask] = np.nan

            outdir = Path.cwd()/tile/band
            outdir.mkdir(exist_ok=True,parents=True)
            fits.writeto(outdir/f"{tile}cut_{band}.fits",data,hdr)
            fits.writeto(outdir/f"{tile}cut_{band}_weight.fits",weight,hdr)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Use a cookie cutter chop away extraneous data on the edges and replace them with NaNs.')
    parser.add_argument('tiles', help='Tiles you want to cut (e.g., tile4 or [tile4,tile5])')
    parser.add_argument('bands', help='Photometric bands (e.g., g or [g,r])')
    args = parser.parse_args()

    cut_tiles(args.tiles, args.bands)