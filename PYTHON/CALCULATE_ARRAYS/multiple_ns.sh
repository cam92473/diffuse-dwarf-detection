#!/bin/bash
python3 construct_arrays.py ../../IMAGES/large_images/center_region.fits ../../IMAGES/large_images/center_region.weight.fits g 17 22 1 50 550 100 0.50 0.75 0.5 1 0 360 100 1 MASTER_CATALOGS/ARTIFICIAL/psfs/KK98a189_psf.fits --verbose --signature n_0.50_0.75 -reff_units pc --no_plot

python3 construct_arrays.py ../../IMAGES/large_images/center_region.fits ../../IMAGES/large_images/center_region.weight.fits g 17 22 1 50 550 100 0.75 1.00 0.5 1 0 360 100 1 MASTER_CATALOGS/ARTIFICIAL/psfs/KK98a189_psf.fits --verbose --signature n_0.75_1.00 -reff_units pc --no_plot

python3 construct_arrays.py ../../IMAGES/large_images/center_region.fits ../../IMAGES/large_images/center_region.weight.fits g 17 22 1 50 550 100 1.00 1.25 0.5 1 0 360 100 1 MASTER_CATALOGS/ARTIFICIAL/psfs/KK98a189_psf.fits --verbose --signature n_1.00_1.25 -reff_units pc --no_plot

python3 construct_arrays.py ../../IMAGES/large_images/center_region.fits ../../IMAGES/large_images/center_region.weight.fits g 17 22 1 50 550 100 1.25 1.50 0.5 1 0 360 100 1 MASTER_CATALOGS/ARTIFICIAL/psfs/KK98a189_psf.fits --verbose --signature n_1.25_1.50 -reff_units pc --no_plot
