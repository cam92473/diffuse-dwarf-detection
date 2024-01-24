import matplotlib.pyplot as plt
import numpy as np
from regions import PixCoord, RectanglePixelRegion
from matplotlib.colors import LogNorm
from modest_image import imshow as modest_imshow
from astropy.io import fits
import gc
import argparse

def region_cutter(filename):

    with fits.open(filename) as hdul:
        data = hdul[0].data

    ax = plt.gca()
    modest_imshow(ax, data, interpolation='none', origin='lower')
    plt.show()

    r, c = data.shape

    total_mask = np.zeros((r,c),dtype=np.uint8)

    rect_center = RectanglePixelRegion(center=PixCoord(x=15691, y=14270), width=29775, height=4617)
    rect_center_mask = rect_center.to_mask(mode='center')
    rect_center_mask_complete = (rect_center_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_center_mask_complete

    del(rect_center)
    del(rect_center_mask)
    del(rect_center_mask_complete)
    gc.collect()
    print("1")

    rect_plus1 = RectanglePixelRegion(center=PixCoord(x=15688, y=18817), width=25497, height=4512)
    rect_plus1_mask = rect_plus1.to_mask(mode='center')
    rect_plus1_mask_complete = (rect_plus1_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_plus1_mask_complete

    del(rect_plus1)
    del(rect_plus1_mask)
    del(rect_plus1_mask_complete)
    gc.collect()
    print("2")

    rect_plus2 = RectanglePixelRegion(center=PixCoord(x=15674, y=22191), width=21287, height=2288)
    rect_plus2_mask = rect_plus2.to_mask(mode='center')
    rect_plus2_mask_complete = (rect_plus2_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_plus2_mask_complete

    del(rect_plus2)
    del(rect_plus2_mask)
    del(rect_plus2_mask_complete)
    gc.collect()
    print("3")

    rect_plus3 = RectanglePixelRegion(center=PixCoord(x=15676, y=24463), width=17030, height=2261)
    rect_plus3_mask = rect_plus3.to_mask(mode='center')
    rect_plus3_mask_complete = (rect_plus3_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_plus3_mask_complete

    del(rect_plus3)
    del(rect_plus3_mask)
    del(rect_plus3_mask_complete)
    gc.collect()
    print("4")

    rect_leftear = RectanglePixelRegion(center=PixCoord(x=11419, y=26717), width=4298, height=2265)
    rect_leftear_mask = rect_leftear.to_mask(mode='center')
    rect_leftear_mask_complete = (rect_leftear_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_leftear_mask_complete

    del(rect_leftear)
    del(rect_leftear_mask)
    del(rect_leftear_mask_complete)
    gc.collect()
    print("5")

    rect_rightear = RectanglePixelRegion(center=PixCoord(x=19927, y=26720), width=4277, height=2283)
    rect_rightear_mask = rect_rightear.to_mask(mode='center')
    rect_rightear_mask_complete = (rect_rightear_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_rightear_mask_complete

    del(rect_rightear)
    del(rect_rightear_mask)
    del(rect_rightear_mask_complete)
    gc.collect()
    print("6")

    rect_minus1 = RectanglePixelRegion(center=PixCoord(x=15718, y=9726), width=25509, height=4530)
    rect_minus1_mask = rect_minus1.to_mask(mode='center')
    rect_minus1_mask_complete = (rect_minus1_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_minus1_mask_complete

    del(rect_minus1)
    del(rect_minus1_mask)
    del(rect_minus1_mask_complete)
    gc.collect()
    print("7")

    rect_minus2 = RectanglePixelRegion(center=PixCoord(x=15736, y=6342), width=21256, height=2290)
    rect_minus2_mask = rect_minus2.to_mask(mode='center')
    rect_minus2_mask_complete = (rect_minus2_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_minus2_mask_complete

    del(rect_minus2)
    del(rect_minus2_mask)
    del(rect_minus2_mask_complete)
    gc.collect()
    print("8")

    rect_minus3 = RectanglePixelRegion(center=PixCoord(x=15726, y=4075), width=17040, height=2284)
    rect_minus3_mask = rect_minus3.to_mask(mode='center')
    rect_minus3_mask_complete = (rect_minus3_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_minus3_mask_complete

    del(rect_minus3)
    del(rect_minus3_mask)
    del(rect_minus3_mask_complete)
    gc.collect()
    print("9")

    rect_leftfoot = RectanglePixelRegion(center=PixCoord(x=11479, y=1821), width=4270, height=2260)
    rect_leftfoot_mask = rect_leftfoot.to_mask(mode='center')
    rect_leftfoot_mask_complete = (rect_leftfoot_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_leftfoot_mask_complete

    del(rect_leftfoot)
    del(rect_leftfoot_mask)
    del(rect_leftfoot_mask_complete)
    gc.collect()
    print("10")

    rect_rightfoot = RectanglePixelRegion(center=PixCoord(x=19981, y=1818), width=4239, height=2340)
    rect_rightfoot_mask = rect_rightfoot.to_mask(mode='center')
    rect_rightfoot_mask_complete = (rect_rightfoot_mask.to_image((r,c))).astype(np.uint8)

    total_mask += rect_rightfoot_mask_complete

    del(rect_rightfoot)
    del(rect_rightfoot_mask)
    del(rect_rightfoot_mask_complete)
    gc.collect()
    print("11")

    rect_bad = RectanglePixelRegion(center=PixCoord(x=2951, y=15364), width=4296, height=2429)
    rect_bad_mask = rect_bad.to_mask(mode='center')
    rect_bad_mask_complete = (rect_bad_mask.to_image((r,c))).astype(np.uint8)

    total_mask -= rect_bad_mask_complete

    del(rect_bad)
    del(rect_bad_mask)
    del(rect_bad_mask_complete)
    gc.collect()
    print("1.5")

    bool_mask = total_mask.astype(bool)
    reverse_bool_mask = ~bool_mask

    ax = plt.gca()
    modest_imshow(ax, reverse_bool_mask, interpolation='none', origin='lower')
    plt.show()

    del(total_mask)
    del(bool_mask)
    gc.collect()

    xi, yi = np.meshgrid(np.arange(c),np.arange(r),copy=False)
    x = xi.astype(np.uint16)

    del(xi)
    del(yi)
    gc.collect()

    badx = x[reverse_bool_mask]

    del(x)
    gc.collect()

    xi, yi = np.meshgrid(np.arange(c),np.arange(r),copy=False)
    y = yi.astype(np.uint16)


    del(xi)
    del(yi)
    gc.collect()

    bady = y[reverse_bool_mask]

    del(y)
    del(reverse_bool_mask)

    gc.collect()

    print("ha")

    data[bady,badx] = np.nan

    hdu = fits.PrimaryHDU(data)
    hdu.writeto('cut_image.fits',overwrite=True)
    
    print("done")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Cut out a region from a larger image and save it as its own fits image.')
    parser.add_argument('filename', help='The filename of the image to cut.')
    args = parser.parse_args()

    region_cutter(args.filename)


           

