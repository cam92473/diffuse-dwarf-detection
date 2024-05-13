#!/bin/bash
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/g/survey_tile4_g_short_ALIGNi.fits tile4cut_g.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/g/survey_tile4_g_short_ALIGNi.WEIGHT.fits tile4cut_g.weight.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/i/survey_tile4_i_short.fits tile4cut_i.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/i/survey_tile4_i_short.WEIGHT.fits tile4cut_i.weight.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/r/survey_tile4_r_short_ALIGNi.fits tile4cut_r.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/r/survey_tile4_r_short_ALIGNi.WEIGHT.fits tile4cut_r.weight.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/z/survey_tile4_z_short_ALIGNi.fits tile4cut_z.fits
python3 region_cutter.py ../../IMAGES/very_large_images/original_data/z/survey_tile4_z_short_ALIGNi.WEIGHT.fits tile4cut_z.weight.fits
