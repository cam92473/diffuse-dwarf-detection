from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import argparse
import re
import matplotlib.pyplot as plt
from pathlib import Path

def dwarf_cutout(filename, location, width, height, outpath):

    hdul = fits.open(filename)
    primary_hdu = hdul[0]
    header = primary_hdu.header
    data = primary_hdu.data

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

    cutout = Cutout2D(data, position=dwarf_position, size=(height,width), wcs=wcs, mode='strict')

    primary_hdu.header.update(cutout.wcs.to_header())
    primary_hdu.data = cutout.data

    project_root = Path.cwd().parents[1]
    full_outpath = project_root/outpath
    outfolder = full_outpath.parents[0]
    outfolder.mkdir(parents=True,exist_ok=True)

    primary_hdu.writeto(full_outpath, overwrite=True)
    print("done")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Cut out a region from a larger image and save it as its own fits image.')
    parser.add_argument('filename', help='The filename of the input image containing the dwarfs.')
    parser.add_argument('location', help='The location of the dwarf. Supply either the ICRS sexagesimal coordinates of the dwarf, given as "[-]##h##m##.##s [-]##d##m##.##s", or a pixel coordinate, given as "#### ####". Be sure to include the quotations around the argument so that argparse interprets the input as a single argument.')
    parser.add_argument('width', type=int, help='The width of the cutout in pixels')
    parser.add_argument('height', type=int, help='The height of the cutout in pixels')
    parser.add_argument('dwarfname', help='The name of the dwarf that can be used as the output fits filename.')
    args = parser.parse_args()

    dwarf_cutout(args.filename, args.location, args.width, args.height, args.dwarfname)