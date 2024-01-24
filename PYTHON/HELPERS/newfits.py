from astropy.io import fits
import numpy as np

data = np.zeros((7200,7200),dtype=np.float32)
hdu = fits.PrimaryHDU(data)
hdul = fits.HDUList([hdu])
hdul.writeto('zeros_center_region.fits',overwrite=True)