from astropy.io import fits
from astropy.wcs import WCS
from regions import RectanglePixelRegion, PixCoord
import argparse
from astropy.nddata import Cutout2D


def split_into_quarters(filename):

    with fits.open(filename) as hdul:
        data = hdul[0].data
        header = hdul[0].header
    
    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']

    xmax, ymax = data.shape[0], data.shape[1]
    xq1, xmid, xq3 = xmax/4, xmax/2, xmax*3/4
    yq1, ymid, yq3 = ymax/4, ymax/2, ymax*3/4
    width = xmid+1000
    height = ymid+1000

    qbl = Cutout2D(data, position=(xq1,yq1), size=(width,height), wcs=wcs)
    qtl = Cutout2D(data, position=(xq1,yq3), size=(width,height), wcs=wcs)
    qtr = Cutout2D(data, position=(xq3,yq3), size=(width,height), wcs=wcs)
    qbr = Cutout2D(data, position=(xq3,yq1), size=(width,height), wcs=wcs)
    
    name = filename.split('/')[-1]
    parts = name.split('_')

    fits.writeto(parts[0]+'_bl_'+parts[1], qbl.data, qbl.wcs.to_header())
    fits.writeto(parts[0]+'_tl_'+parts[1], qtl.data, qtl.wcs.to_header())
    fits.writeto(parts[0]+'_tr_'+parts[1], qtr.data, qtr.wcs.to_header())
    fits.writeto(parts[0]+'_br_'+parts[1], qbr.data, qbr.wcs.to_header())


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('filename', help='Filename of the data image, including the .fits extension.')

    args = parser.parse_args()
    filename = args.filename

    split_into_quarters(filename)