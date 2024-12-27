from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import argparse
import re
from pathlib import Path

def dwarf_cutout(tile, band, location, width, height, dwarfname):

    data_file = Path.cwd()/'tiles'/tile/band/f'tile4cut_{band}.fits'
    weight_file = Path.cwd()/'tiles'/tile/band/f'tile4cut_{band}_weight.fits'
    with fits.open(data_file) as hdul:
        header = hdul[0].header
        data = hdul[0].data
    with fits.open(weight_file) as hdul:
        weight = hdul[0].data

    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']

    if re.search("\d{2}h\d{2}m.+s\s\-\d{2}d\d{2}m.+s", location) is not None:
        sexcoord = location
    elif re.search("\d+\s\d+", location) is not None:
        pixelcoord = location.split()
        x, y = int(pixelcoord[0]), int(pixelcoord[1])
        sexcoord = wcs.pixel_to_world(x,y)
    else:
        raise ValueError("Could not identify the location from the supplied second parameter. Enter either a coordinate in sexigesimal notation or a pixel coordinate.")

    dwarf_position = SkyCoord(sexcoord, frame='icrs')

    data_cutout = Cutout2D(data, position=dwarf_position, size=(height,width), wcs=wcs, mode='strict')
    weight_cutout = Cutout2D(weight, position=dwarf_position, size=(height,width), wcs=wcs, mode='strict')

    header.update(data_cutout.wcs.to_header())

    folder = Path.cwd()/'created_images'/'raw_images'/tile/'real'

    fits.writeto(folder/'data'/f'{dwarfname}.fits', data_cutout.data, header, overwrite=True)
    fits.writeto(folder/'weight'/f'{dwarfname}_weight.fits', weight_cutout.data, header, overwrite=True)
    print("done")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Cut out a region from a larger image and save it as its own fits image.')
    parser.add_argument('tile', help='The tile you want to make the cutout from (e.g., "tile4")')
    parser.add_argument('band', help='The photometric band of the tile.')
    parser.add_argument('location', help='The location of the dwarf. Supply either the ICRS sexagesimal coordinates of the dwarf, given as "[-]##h##m##.##s [-]##d##m##.##s", or a pixel coordinate, given as "#### ####". Be sure to include the quotations around the argument so that argparse interprets the input as a single argument.')
    parser.add_argument('width', type=int, help='The width of the cutout in pixels')
    parser.add_argument('height', type=int, help='The height of the cutout in pixels')
    parser.add_argument('dwarfname', help='The name of the dwarf cutout. Do not include the fits extension.')
    args = parser.parse_args()

    dwarf_cutout(args.tile, args.band, args.location, args.width, args.height, args.dwarfname)