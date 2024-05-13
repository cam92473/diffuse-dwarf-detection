from astropy.io import fits
import numpy as np

name = "200x200"
img = np.zeros((200,200))
fits.writeto(f'zeros_{name}.fits',img)