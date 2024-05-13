# Copyright (c) 2012-2023 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#
"""
Demo #3

The third script in our tutorial about using GalSim in python scripts: examples/demo*.py.
(This file is designed to be viewed in a window 100 characters wide.)

This script gets reasonably close to including all the principal features of an image
from a ground-based telescope.  The galaxy is represented as the sum of a bulge and a disk,
where each component is represented by a sheared Sersic profile (with different Sersic
indices).  The PSF has both atmospheric and optical components.  The atmospheric
component is a Kolmogorov turbulent spectrum.  The optical component includes defocus,
coma and astigmatism, as well as obscuration from a secondary mirror.  The noise model
includes both a gain and read noise.  And finally, we include the effect of a slight
telescope distortion.

New features introduced in this demo:

- obj = galsim.Sersic(n, flux, half_light_radius)
- obj = galsim.Sersic(n, flux, scale_radius)
- obj = galsim.Kolmogorov(fwhm)
- obj = galsim.OpticalPSF(lam_over_diam, defocus, coma1, coma2, astig1, astig2, obscuration)
- obj = obj.shear(e, beta)  -- including how to specify an angle in GalSim
- shear = galsim.Shear(q, beta)
- obj = obj.shear(shear)
- obj3 = x1 * obj1 + x2 * obj2
- obj = obj.withFlux(flux)
- image = galsim.ImageF(image_size, image_size)
- image = obj.drawImage(image, wcs)
- image = obj.drawImage(method='sb')
- world_profile = wcs.toWorld(profile)
- shear3 = shear1 + shear2
- noise = galsim.CCDNoise(rng, sky_level, gain, read_noise)
"""

import sys
import os
import math
import logging
import galsim
from astropy.io import fits

def main(argv):
    """
    Getting reasonably close to including all the principle features of an image from a
    ground-based telescope:
      - Use a bulge plus disk model for the galaxy
      - Both galaxy components are Sersic profiles (n=3.5 and n=1.5 respectively)
      - Let the PSF have both atmospheric and optical components.
      - The atmospheric component is a Kolmogorov spectrum.
      - The optical component has some defocus, coma, and astigmatism.
      - Add both Poisson noise to the image and Gaussian read noise.
      - Let the pixels be slightly distorted relative to the sky.
    """

    gal_flux = 68000
    #gal_flux = 109294        # ADU  ("Analog-to-digital units", the units of the numbers on a CCD)
    n = 0.8001                  #
    re = 15.2273               # arcsec
    q = 0.8804           # (axis ratio 0 < q < 1)
    beta = 48.8776          # degrees (position angle on the sky)
    atmos_fwhm=2.1         # arcsec
    atmos_e = 0.13         #
    atmos_beta = 0.81      # radians
    opt_defocus=0.53       # wavelengths
    opt_a1=-0.29           # wavelengths
    opt_a2=0.12            # wavelengths
    opt_c1=0.64            # wavelengths
    opt_c2=-0.33           # wavelengths
    opt_obscuration=0.3    # linear scale size of secondary mirror obscuration
    lam = 800              # nm    NB: don't use lambda - that's a reserved word.
    tel_diam = 4.          # meters
    pixel_scale = 0.263     # arcsec / pixel
    model_size = 833        # n x n pixels
    psf_size = 75
    wcs_g1 = -0.02         #
    wcs_g2 = 0.01          #
    sky_level = 2.5e4      # ADU / arcsec^2
    gain = 5             # e- / ADU
                           # Note: here we assume 1 photon -> 1 e-, ignoring QE.  If you wanted,
                           # you could include the QE factor as part of the gain.
    read_noise = 8       # e- / pixel

    #random_seed = galsim.BaseDeviate(1314662).raw()
    #rng = galsim.BaseDeviate(random_seed+1)

    gal = galsim.Sersic(n, half_light_radius=re)
    gal_shape = galsim.Shear(q=q, beta=beta*galsim.degrees)
    gal = gal.shear(gal_shape)
    gal = gal.withFlux(gal_flux)

    with fits.open('KK98a189.PSF.fits') as hdul:
        data = hdul[0].data
    psf = galsim.InterpolatedImage(galsim.Image(data,scale=0.263))

    final = galsim.Convolve([gal,psf])
    #wcs = galsim.ShearWCS(scale=pixel_scale, shear=galsim.Shear(g1=wcs_g1, g2=wcs_g2))
    im = galsim.ImageF(model_size, model_size, scale=0.263)
    image = final.drawImage(image=im)
    im_epsf = galsim.ImageF(psf_size, psf_size, scale=0.263)
    image_epsf = psf.drawImage(image=im_epsf)

    # The sky level for CCDNoise is the level per pixel that contributed to the noise.
    #sky_level_pixel = sky_level * pixel_scale**2
    #noise = galsim.CCDNoise(rng, gain=gain, read_noise=read_noise)
    #image.addNoise(noise)

    # Write the images to files.
    file_name = os.path.join('output', 'gal.fits')
    file_name_epsf = os.path.join('output','gal_epsf.fits')
    image.write(file_name)
    image_epsf.write(file_name_epsf)

    # Check that the HSM package, which is bundled with GalSim, finds a good estimate
    # of the shear.
    results = galsim.hsm.EstimateShear(image, image_epsf)

if __name__ == "__main__":
    main(sys.argv)
