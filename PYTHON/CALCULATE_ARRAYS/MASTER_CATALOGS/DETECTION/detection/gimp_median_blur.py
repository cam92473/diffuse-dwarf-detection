#!/usr/bin/env python
from gimpfu import *

def gimp_median_blur(in_path,kernelrad):
  image = pdb.file_fits_load(in_path, in_path)
  active_layer = pdb.gimp_image_get_active_layer(image)
  print("blurring...")
  pdb.python_gegl(image, active_layer, "median-blur radius=%i percentile=50 high-precision=1" %kernelrad)
  return image, active_layer

  