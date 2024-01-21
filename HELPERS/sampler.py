from astropy.io import fits
import numpy as np
from numpy.random import uniform, randint
from modest_image import imshow as modest_imshow
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

with fits.open('tile4cut.fits') as hdul:
    data = hdul[0].data

ax = plt.subplot()
modest_imshow(ax, data, interpolation='none', origin='lower', norm=LogNorm(vmin=1,vmax=150))

plt.show()

r, c = data.shape
print(r,c)

num_dwarfs=100

dwarf_x0s = np.zeros(num_dwarfs,dtype=int)
dwarf_y0s = np.zeros(num_dwarfs,dtype=int)
s = 0
while s < num_dwarfs:
    thisr, thisc = randint(r), randint(c)
    if data[thisr,thisc] != -5:
        dwarf_x0s[s] = thisc
        dwarf_y0s[s] = thisr
        s += 1

ax = plt.gca()
modest_imshow(ax, data, interpolation='none', origin='lower', norm=LogNorm(vmin=1,vmax=150))
ax.scatter(dwarf_x0s,dwarf_y0s,marker='+',color='r')

plt.show()