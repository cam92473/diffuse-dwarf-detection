#!/usr/bin/env python
from gimpfu import *

def gimp_median_blur(in_path,kernelrad,out_path):
  image = pdb.file_fits_load(in_path, in_path)
  active_layer = pdb.gimp_image_get_active_layer(image)
  pdb.python_gegl(image, active_layer, "median-blur radius=%i percentile=50 high-precision=1" %kernelrad)
  pdb.file_fits_save(image, active_layer, out_path, out_path)
  pdb.gimp_quit(1)
  
register(
  "python-fu-median-blur",
  "",
  "",
  "",
  "",
  "",
  "Python-Fu Median Blur...",
  "",
  [
    (PF_FILENAME, "in_path", "Input file path", ""),
    (PF_INT, "kernelrad", "Kernel Radius", 30),
    (PF_FILENAME, "out_path", "Output file path", "")
  ],
  [],
  gimp_median_blur, menu="<Image>/Filters/Blur"
)

main()