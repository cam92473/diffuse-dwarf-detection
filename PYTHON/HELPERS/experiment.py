import numpy as np
from astropy.modeling.models import Sersic2D
from astropy.io import fits
from astropy.convolution import convolve
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt

with fits.open('KK98a189_psf.fits') as hdul:
    psf_phdu = hdul[0]
    psfkernel = psf_phdu.data

image_dimensions = (1000,1000)
data = np.zeros(image_dimensions)
data2 = np.zeros(image_dimensions)

Ieff_pix = np.array([1,1,2,2,3,3])
reff_pix = np.array([25,20,45,25,30,60])
n = np.array([1,0.8,1.2,1.1,1,1.5])
x0 = np.array([100,300,240,550,400,670])
y0 = np.array([150,630,500,350,100,700])
ellip = np.array([0,0.2,0.5,0.3,0,0.1])
thetarad = np.array([0,0.123,0.523,1.2,0.42,0])

num_dwarfs = 6

sizefactor = 5
sticker_left, sticker_right = x0-sizefactor*reff_pix, x0+sizefactor*reff_pix+1
sticker_left, sticker_right = np.where(sticker_left<0,0,sticker_left), np.where(sticker_right>image_dimensions[1],image_dimensions[1],sticker_right)
sticker_bottom, sticker_top = y0-sizefactor*reff_pix, y0+sizefactor*reff_pix+1
sticker_bottom, sticker_top = np.where(sticker_bottom<0,0,sticker_bottom), np.where(sticker_top>image_dimensions[0],image_dimensions[0],sticker_top)

canvas = np.zeros((1000,1000))
x, y = np.meshgrid(np.arange(1000), np.arange(1000), copy=False)
for i in range(num_dwarfs):
    model = Sersic2D(amplitude=Ieff_pix[i], r_eff=reff_pix[i], n=n[i], x_0=x0[i], y_0=y0[i], ellip=ellip[i], theta=thetarad[i])
    canvas[y,x] += model(x, y)
conv_canvas = convolve(canvas, psfkernel)
data += conv_canvas

for i in range(num_dwarfs):
    model = Sersic2D(amplitude=Ieff_pix[i], r_eff=reff_pix[i], n=n[i], x_0=x0[i], y_0=y0[i], ellip=ellip[i], theta=thetarad[i])
    sticker_x = np.arange(sticker_left[i], sticker_right[i])
    sticker_y = np.arange(sticker_bottom[i], sticker_top[i])
    x, y = np.meshgrid(sticker_x, sticker_y, copy=False)
    sticker = model(x, y)
    conv_sticker = convolve(sticker, psfkernel)
    data2[y,x] += conv_sticker

fig, axs = plt.subplots(1,3,figsize=(15,5))
axs[0].imshow(data,origin='lower',interpolation='none',norm=LogNorm())
axs[0].set_title('')
axs[1].imshow(data2,origin='lower',interpolation='none',norm=LogNorm())
axs[2].imshow(data-data2,origin='lower',interpolation='none',norm=LogNorm(vmin=np.min(data),vmax=np.max(data)))
plt.show()