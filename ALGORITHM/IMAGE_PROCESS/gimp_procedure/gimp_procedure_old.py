#!/usr/bin/python
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gegl, Gio
import time
from pathlib import Path

"""
------------ ****** GIMP PROCEDURE ****** ------------
    >> load fits file (gimp-ready) and display it
    >> pick NaN color and store as foreground color
    >> crop away NaN border
    >> select non-NaN region and save it as a channel
    >> optionally, create a copy of the original layer, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> create a copy of the original layer
    >> obtain the median color of the non-NaN region in the copy layer and set the background color to this (due to a Gimp bug, you must set it to white (or something contrasting) first)
    >> test if the NaN region in the copy layer is not empty (exists), and if so, fill it with the median color (to prevent NaN bleeding)
    >> gaussian blur the copy of the original layer (to attenuate high frequencies a bit)
    >> run a wavelet decompose on the blurred copy
    >> create new layers from the lowpass component (lowest, residual frequency) and the highpass component (3rd highest frequency), copying the lowpass component
    >> for reasons that have to do with a bug in thresholding in Gimp, convert image to perceptual lighting
    >> threshold the highpass component using its mean and std, creating a mask
    >> grow and flood the mask and then apply it to the original layer (deleting those pixels in the original layer)
    >> threshold the lowpass component usings its mean and std, creating a mask
    >> grow and flood the mask and then apply it to the original layer (deleting those pixels in the original layer)
    >> use the bloom and shadows-highlights operations on the lowpass copy before thresholding usings its mean, to obtain a mask for extended halo objects
    >> flood mask and appy it to the original layer (deleting those pixels in the original layer)
    >> convert image back to linear lighting
    >> create a blank new layer
    >> get the (new) median color of the (now masked) original layer and bucket fill the new layer with this color
    >> add noise to the new layer using the std of the original layer
    >> merge the two layers, filling in the mask of the original layer with the noisy constant median color
    >> optionally, create a copy of this merged layer, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> obtain the median color of the non-NaN region in the merged layer and set the background color to this (due to a Gimp bug, you must set it to white (or something contrasting) first)
    >> test if the NaN region in the merged layer is not empty (exists), and if so, fill it with the (new) median color (to prevent NaN bleeding)
    >> median blur the merged layer with the smaller of the two user-input kernels
    >> optionally, create a copy of this median-blurred layer, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> create a copy of the merged layer
    >> median blur the merged layer copy with the larger of the two user-input kernels
    >> optionally, create a copy of this median-blurred layer copy, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> if the NaN region in (either of the) median-blurred layers is not empty (exists), fill it with the foreground NaN color
    >> set the foreground color to black (for Gimp bug reasons)
    >> export the image as a fits file to a directory labelled ("blurred"). With the smaller-median-kernel layer on top, this will save the smaller median blurred image
    >> delete the top layer (the smaller-median-kernel layer)
    >> export the image again as a fits file to a directory labelled ("blurred"). With only the larger-median-kernel layer now, this will save the larger median blurred image
    >> delete display and image and exit Gimp

"""

def gimp_procedure(data_path,blurred_path,save_path,medblur_radii,save,play_through,signature,verbosity):
        sleeptime = 1

        if verbosity > 0:
                print(" opening image...")

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-load')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('file', Gio.file_new_for_path(data_path))
        result = procedure.run(config)
        image = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-display-new')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        display = result.index(1)

        original = image.get_layers()[0]

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-pick-color')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('num-drawables', 1)
        config.set_property('drawables', Gimp.ObjectArray.new(Gimp.Drawable, [original], False))
        config.set_property('x', 0)
        config.set_property('y', 0)
        config.set_property('sample-merged', 0)
        config.set_property('sample-average', 0)
        config.set_property('average-radius', 0)
        result = procedure.run(config)
        nancolor = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-foreground')
        config = procedure.create_config()
        config.set_property('foreground', nancolor)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-crop')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('new-width', image.get_width()-2)
        config.set_property('new-height', image.get_height()-2)
        config.set_property('offx', 1)
        config.set_property('offy', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-sample-threshold')
        config = procedure.create_config()
        config.set_property('sample-threshold', 0)
        result = procedure.run(config)

        black = Gegl.Color()
        black.set_rgba(0,0,0,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-color')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 0)
        config.set_property('drawable', original)
        config.set_property('color', black)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-flood')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-save')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        nonnan_channel = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-get-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        precision = result.index(1)

        if precision.real != 600:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
                config = procedure.create_config()
                config.set_property('image', image)
                config.set_property('precision', 600)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original)
        result = procedure.run(config)
        original_save = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_save)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', original)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        median = result.index(3)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels')
        config = procedure.create_config(); config.set_property('drawable', original_save)
        config.set_property('channel', 0)
        config.set_property('low-input', median-0.015)
        config.set_property('high-input', median+0.015)
        config.set_property('clamp-input', False)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0)
        config.set_property('high-output', 1)
        config.set_property('clamp-output', False)
        result = procedure.run(config) 

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  image ready")
                time.sleep(sleeptime)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_path)/f'{signature}_A_data.jpeg')))
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_save)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        original_copy = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_copy)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        white = 1.
        white_color = Gegl.Color()
        white_color.set_rgba(white,white,white,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', white_color)
        result = procedure.run(config)

        median_color = Gegl.Color()
        median_color.set_rgba(median,median,median,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', median_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-is-empty')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        is_empty = result.index(1)

        if not is_empty:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', original_copy)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        if verbosity > 0:
                print(" gaussian blur...")

        Gegl.init()

        buffer = original_copy.get_buffer()
        shadow = original_copy.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        gauss = graph.create_child("gegl:gaussian-blur")
        gauss.set_property("std-dev-x",2.5)
        gauss.set_property("std-dev-y",2.5)
        gauss.set_property("filter",'FIR')
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(gauss)
        gauss.link(write)
        write.process()
        shadow.flush()
        original_copy.merge_shadow(True)
        original_copy.update(0,0,original_copy.get_width(),original_copy.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  finished Gaussian blur")
                time.sleep(sleeptime)

        if verbosity > 0:
                print(" wavelet decompose...")

        procedure = Gimp.get_pdb().lookup_procedure('plug-in-wavelet-decompose')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('num-drawables', 1)
        config.set_property('drawables', Gimp.ObjectArray.new(Gimp.Drawable, [original_copy], False))
        config.set_property('scales', 5)
        config.set_property('create-group', 1)
        config.set_property('create-masks', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-get-layer-by-name')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('name', 'Scale 1')
        freq1 = procedure.run(config).index(1)
        config.set_property('name', 'Scale 2')
        freq2 = procedure.run(config).index(1)
        config.set_property('name', 'Scale 3')
        freq3 = procedure.run(config).index(1)
        config.set_property('name', 'Scale 4')
        freq4 = procedure.run(config).index(1)
        config.set_property('name', 'Scale 5')
        freq5 = procedure.run(config).index(1)
        config.set_property('name', 'Residual')
        residual = procedure.run(config).index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', freq1)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', freq2)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', freq3)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', freq4)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', freq5)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', residual)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-new-from-visible')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('dest-image', image)
        config.set_property('name', 'Lowpass')
        result = procedure.run(config)
        lowpass = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', lowpass)
        config.set_property('parent', None)
        config.set_property('position', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  lowpass component")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', lowpass)
        result = procedure.run(config)
        lowpass_copy = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', lowpass_copy)
        config.set_property('parent', None)
        config.set_property('position', 2)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', residual)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', freq3)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-new-from-visible')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('dest-image', image)
        config.set_property('name', 'Highpass')
        result = procedure.run(config)
        highpass = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', highpass)
        config.set_property('parent', None)
        config.set_property('position', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  highpass component")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-get-layer-by-name')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('name', 'Decomposition')
        result = procedure.run(config)
        decomposition = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', decomposition)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-has-alpha')
        config = procedure.create_config()
        config.set_property('drawable', original)
        result = procedure.run(config)
        has_alpha = result.index(1)

        if not has_alpha:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-alpha')
                config = procedure.create_config()
                config.set_property('layer', original)
                result = procedure.run(config)

        if verbosity > 0:
                print(" thresholding & masking...")    

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('precision', 650)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', highpass)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        highpass_thresh = mean + 2*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', highpass)
        config.set_property('channel', 0)
        config.set_property('low-threshold', highpass_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  highpass mask")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', lowpass)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', lowpass_copy)
        config.set_property('visible', False)
        result = procedure.run(config)
        config.set_property('item', original_copy)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', highpass)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        highpass_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', highpass)
        config.set_property('mask', highpass_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', highpass_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 10)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-flood')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 3)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', highpass)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  mask expanded and flooded")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  cleared masked region in original image")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', lowpass)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', lowpass)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        lowpass_thresh = mean + 2*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', lowpass)
        config.set_property('channel', 0)
        config.set_property('low-threshold', lowpass_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  lowpass mask")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', lowpass)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        lowpass_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', lowpass)
        config.set_property('mask', lowpass_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', lowpass_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 10)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-flood')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 3)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', lowpass)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  mask expanded and flooded")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  cleared masked region in original image")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', lowpass_copy)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', lowpass_copy)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        Gegl.init()

        buffer = lowpass_copy.get_buffer()
        shadow = lowpass_copy.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        bloom = graph.create_child("gegl:bloom")
        bloom.set_property("threshold",100*(mean-0.1*std_dev))
        bloom.set_property("softness",15)
        bloom.set_property("radius",25)
        bloom.set_property("strength",200)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(bloom)
        bloom.link(write)
        write.process()
        shadow.flush()
        lowpass_copy.merge_shadow(True)
        lowpass_copy.update(0,0,lowpass_copy.get_width(),lowpass_copy.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-shadows-highlights')
        config = procedure.create_config()
        config.set_property('drawable', lowpass_copy)
        config.set_property('shadows', -100)
        config.set_property('highlights', 0)
        config.set_property('whitepoint', 0)
        config.set_property('radius', 100)
        config.set_property('compress', 50)
        config.set_property('shadows-ccorrect', 100)
        config.set_property('highlights-ccorrect', 50)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', lowpass_copy)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        halos_thresh = 1.5*mean
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', lowpass_copy)
        config.set_property('channel', 0)
        config.set_property('low-threshold', halos_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  large halos mask")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', lowpass_copy)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        largehalos_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', lowpass_copy)
        config.set_property('mask', largehalos_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', largehalos_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-flood')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 3)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', lowpass_copy)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  mask flooded")
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', highpass)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', lowpass)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', lowpass_copy)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_copy)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  cleared masked region in original image")
                time.sleep(sleeptime)

        if verbosity > 0:
                print(" filling mask with background...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('precision', 600)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-new')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('width', image.get_width())
        config.set_property('height', image.get_height())
        config.set_property('type', 2)
        config.set_property('name', 'BGfill')
        config.set_property('opacity', 100)
        config.set_property('mode', 0)
        result = procedure.run(config)
        bgfill = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', bgfill)
        config.set_property('parent', None)
        config.set_property('position', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 0)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)  

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', original)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        std_dev = result.index(2)
        median_masked = result.index(3)

        white = 1.
        white_color = Gegl.Color()
        white_color.set_rgba(white,white,white,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', white_color)
        result = procedure.run(config)

        median_masked_color = Gegl.Color()
        median_masked_color.set_rgba(median_masked,median_masked,median_masked,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', median_masked_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-bucket-fill')
        config = procedure.create_config()
        config.set_property('drawable', bgfill)
        config.set_property('fill-type', 1)
        config.set_property('x', 0)
        config.set_property('y', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('plug-in-rgb-noise')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('drawable', bgfill)
        config.set_property('independent', 0)
        config.set_property('correlated', 0)
        config.set_property('noise-1', std_dev*1.75)
        config.set_property('noise-2', 0)
        config.set_property('noise-3', 0)
        config.set_property('noise-4', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', original)
        config.set_property('merge-type', 0)
        result = procedure.run(config)
        merged_layer = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', image.get_layers()[-1])
        result = procedure.run(config)
        masked_save = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', masked_save)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels')
        config = procedure.create_config(); config.set_property('drawable', masked_save)
        config.set_property('channel', 0)
        config.set_property('low-input', median_masked-0.015)
        config.set_property('high-input', median_masked+0.015)
        config.set_property('clamp-input', False)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0)
        config.set_property('high-output', 1)
        config.set_property('clamp-output', False)
        result = procedure.run(config) 

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  created background and merged with original")
                time.sleep(sleeptime)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_path)/f'{signature}_B_masked.jpeg')))
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', masked_save)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', merged_layer)
        result = procedure.run(config)
        merged_layer_copy = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', merged_layer_copy)
        config.set_property('parent', None)
        config.set_property('position', 1)
        result = procedure.run(config)

        if verbosity > 0:
                print(f" median filtering (kernel size = {medblur_radii[0]})...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-is-empty')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        is_empty = result.index(1)

        if not is_empty:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', merged_layer)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        Gegl.init()

        buffer = merged_layer.get_buffer()
        shadow = merged_layer.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        median_sm = graph.create_child("gegl:median-blur")
        median_sm.set_property("radius",medblur_radii[0])
        median_sm.set_property("high-precision",True)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(median_sm)
        median_sm.link(write)
        write.process()
        shadow.flush()
        merged_layer.merge_shadow(True)
        merged_layer.update(0,0,merged_layer.get_width(),merged_layer.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', merged_layer)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        std_dev = result.index(2)
        median_blur_sm = result.index(3)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', merged_layer)
        config.set_property('add-alpha', True)
        result = procedure.run(config)
        median_blur_sm_save = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_blur_sm_save)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels')
        config = procedure.create_config(); config.set_property('drawable', median_blur_sm_save)
        config.set_property('channel', 0)
        config.set_property('low-input', median_blur_sm-0.005)
        config.set_property('high-input', median_blur_sm+0.005)
        config.set_property('clamp-input', False)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0)
        config.set_property('high-output', 1)
        config.set_property('clamp-output', False)
        result = procedure.run(config) 

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print(f"  finished median filtering (kernel size = {medblur_radii[0]})")
                time.sleep(sleeptime)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_path)/f'{signature}_C_blur{medblur_radii[0]}.jpeg')))
                result = procedure.run(config)                

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_blur_sm_save)
        result = procedure.run(config)

        if verbosity > 0:
                print(f" median filtering (kernel size = {medblur_radii[1]})...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-is-empty')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        is_empty = result.index(1)

        if not is_empty:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', merged_layer_copy)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        Gegl.init()

        buffer = merged_layer_copy.get_buffer()
        shadow = merged_layer_copy.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        median_lg = graph.create_child("gegl:median-blur")
        median_lg.set_property("radius",medblur_radii[1])
        median_lg.set_property("high-precision",True)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(median_lg)
        median_lg.link(write)
        write.process()
        shadow.flush()
        merged_layer_copy.merge_shadow(True)
        merged_layer_copy.update(0,0,merged_layer_copy.get_width(),merged_layer_copy.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', merged_layer_copy)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        std_dev = result.index(2)
        median_blur_lg = result.index(3)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', merged_layer_copy)
        config.set_property('add-alpha', True)
        result = procedure.run(config)
        median_blur_lg_save = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_blur_lg_save)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels')
        config = procedure.create_config(); config.set_property('drawable', median_blur_lg_save)
        config.set_property('channel', 0)
        config.set_property('low-input', median_blur_lg-0.005)
        config.set_property('high-input', median_blur_lg+0.005)
        config.set_property('clamp-input', False)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0)
        config.set_property('high-output', 1)
        config.set_property('clamp-output', False)
        result = procedure.run(config) 

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print(f"  finished median filtering (kernel size = {medblur_radii[1]})")
                time.sleep(sleeptime)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_path)/f'{signature}_D_blur{medblur_radii[1]}.jpeg')))
                result = procedure.run(config)                

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_blur_lg_save)
        result = procedure.run(config)

        if verbosity > 0:
                print(" saving & exiting gimp...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-is-empty')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        is_empty = result.index(1)

        if not is_empty:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', merged_layer)
                config.set_property('fill-type', 0)
                result = procedure.run(config)

                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', merged_layer_copy)
                config.set_property('fill-type', 0)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-foreground')
        config = procedure.create_config()
        config.set_property('foreground', black)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-flatten')
        config = procedure.create_config()
        config.set_property('layer', merged_layer)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-flatten')
        config = procedure.create_config()
        config.set_property('layer', merged_layer_copy)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', merged_layer_copy)
        config.set_property('add-alpha', False)
        result = procedure.run(config)
        merged_layer_copy_reserved = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', merged_layer_copy)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-export')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('file', Gio.file_new_for_path(str(Path(blurred_path)/f'{signature}_blur{medblur_radii[0]}.fits')))
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', merged_layer)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', merged_layer_copy_reserved)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-export')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('file', Gio.file_new_for_path(str(Path(blurred_path)/f'{signature}_blur{medblur_radii[1]}.fits')))
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-display-delete')
        config = procedure.create_config()
        config.set_property('display', display)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-delete')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
                
        procedure = Gimp.get_pdb().lookup_procedure('gimp-quit')
        config = procedure.create_config()
        config.set_property('force', 1)
        result = procedure.run(config)
