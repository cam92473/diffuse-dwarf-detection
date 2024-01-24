import numpy as np
from astropy.modeling.models import Sersic2D
from astropy.io import fits
from astropy.convolution import convolve
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt
from scipy.signal import fftconvolve

with fits.open('KK98a189_psf.fits') as hdul:
    psf_phdu = hdul[0]
    psfkernel = psf_phdu.data

image_dimensions = (30000,30000)
#data = np.zeros(image_dimensions)

Ieff_pix = np.array([1,1,2,2,3,3])
reff_pix = np.array([25,20,45,25,30,60])
n = np.array([1,0.8,1.2,1.1,1,1.5])
x0 = np.array([100,300,240,550,400,670])
y0 = np.array([150,630,500,350,100,700])
ellip = np.array([0,0.2,0.5,0.3,0,0.1])
thetarad = np.array([0,0.123,0.523,1.2,0.42,0])
num_dwarfs = 6

canvas = np.zeros(image_dimensions)
print("done making canvas")
x, y = np.meshgrid(np.arange(image_dimensions[1]), np.arange(image_dimensions[0]), copy=False)
print("done making meshgrid")
for i in range(num_dwarfs):
    print(i)
    model = Sersic2D(amplitude=Ieff_pix[i], r_eff=reff_pix[i], n=n[i], x_0=x0[i], y_0=y0[i], ellip=ellip[i], theta=thetarad[i])
    canvas[y,x] += model(x, y)
print("done all")
#conv_canvas = convolve(canvas, psfkernel)
#data += conv_canvas

'''for i in range(num_dwarfs):
    model = Sersic2D(amplitude=Ieff_pix[i], r_eff=reff_pix[i], n=n[i], x_0=x0[i], y_0=y0[i], ellip=ellip[i], theta=thetarad[i])
    x, y = np.meshgrid(sticker_x, sticker_y, copy=False)
    sticker = model(x, y)
    conv_sticker = convolve(sticker, psfkernel)
    data2[y,x] += conv_sticker'''

fig, ax = plt.subplots(figsize=(15,5))
ax.imshow(canvas,origin='lower',interpolation='none',norm=LogNorm())
plt.show()

