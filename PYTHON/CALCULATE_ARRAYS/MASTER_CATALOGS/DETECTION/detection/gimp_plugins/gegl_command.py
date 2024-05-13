#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gimpfu import *
from sys import platform
from ctypes import *

def load_library (library_name):
	if platform == "linux" or platform == "linux2":
		library_name = library_name + '.so.0'
	elif platform == "win32":
		from ctypes.util import find_library
		library_name = find_library (library_name + "-0")
	else:
		raise BaseException ("TODO")
	return CDLL (library_name)

gimpC = load_library ('libgimp-2.0')


def gegl_command(image, drawable, gegl_graph_string):
	
	class GeglBuffer(Structure):
		pass
	drawable_id = drawable.ID
	
	gegl = load_library ('libgegl-0.4')
	gegl.gegl_init (None, None)
	gimpC.gimp_drawable_get_shadow_buffer.restype = POINTER (GeglBuffer)
	gimpC.gimp_drawable_get_buffer.restype        = POINTER (GeglBuffer)

	x = c_int (); y = c_int (); w = c_int (); h = c_int ()
	non_empty,x,y,w,h = pdb.gimp_drawable_mask_intersect (drawable)
	args = [b"string", c_char_p (gegl_graph_string), c_void_p ()]
	
	if non_empty:
		source = gimpC.gimp_drawable_get_buffer (drawable_id)
		target = gimpC.gimp_drawable_get_shadow_buffer (drawable_id)
		gegl.gegl_render_op (source, target, "gegl:gegl", *args)
		gegl.gegl_buffer_flush (target)
		gimpC.gimp_drawable_merge_shadow (drawable_id, PushUndo = True)
		gimpC.gimp_drawable_update (drawable_id, x, y, w, h)
		gimpC.gimp_displays_flush ()

register(
	"python_gegl", # name
	'gegl_command', # 
	"gegl_command . . .", # help
	"paynekj", # author
	"paynekj", # copyright
	"2021", # date
	'gegl_command', # menu name
	"RGB,RGBA", 
	[
		(PF_IMAGE, "image",       "Input image", None),
		(PF_DRAWABLE, "drawable", "Input drawable", None),
		(PF_TEXT, "gegl_graph_string", 'gegl_graph_string', ''),
	],
	[],
	gegl_command,
)

main()
