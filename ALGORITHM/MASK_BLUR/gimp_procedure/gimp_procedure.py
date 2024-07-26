#!/usr/bin/python
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gegl, Gio

import time

def gimp_procedure(data_path,blurred_path,save_data_path,save_masked_path,save_blurred_path,medblur_rad,save,play_through,verbosity):
        sleeptime = 1

        if verbosity > 0:
                print(" opening image...")

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-load')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('file', Gio.file_new_for_path(data_path))
        result = procedure.run(config)
        image = result.index(1)

        if play_through:
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', nancolor)
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
        
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels-stretch')
        config = procedure.create_config()
        config.set_property('drawable', original_save)
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
                config.set_property('file', Gio.file_new_for_path(save_data_path))
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', original)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        median = result.index(3)

        median_color = Gegl.Color()
        median_color.set_rgba(median,median,median,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-foreground')
        config = procedure.create_config()
        config.set_property('foreground', median_color)
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
                config.set_property('fill-type', 0)
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
        config.set_property('item', freq1)
        config.set_property('visible', True)
        result = procedure.run(config)
        config.set_property('item', freq2)
        config.set_property('visible', True)
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

        highpass_thresh = mean + 4*std_dev
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
        config.set_property('steps', 5)
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

        largehalos_thresh = mean + 12*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', lowpass_copy)
        config.set_property('channel', 0)
        config.set_property('low-threshold', largehalos_thresh)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 120)
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
        config.set_property('position', 5)
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
        median = result.index(3)

        new_median_color = Gegl.Color()
        new_median_color.set_rgba(median,median,median,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-foreground')
        config = procedure.create_config()
        config.set_property('foreground', new_median_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-bucket-fill')
        config = procedure.create_config()
        config.set_property('drawable', bgfill)
        config.set_property('fill-type', 0)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels-stretch')
        config = procedure.create_config()
        config.set_property('drawable', masked_save)
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
                config.set_property('file', Gio.file_new_for_path(save_masked_path))
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', masked_save)
        result = procedure.run(config)

        if verbosity > 0:
                print(f" median filtering (kernel size = {medblur_rad})...")

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
        median = graph.create_child("gegl:median-blur")
        median.set_property("radius",medblur_rad)
        median.set_property("high-precision",True)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(median)
        median.link(write)
        write.process()
        shadow.flush()
        merged_layer.merge_shadow(True)
        merged_layer.update(0,0,merged_layer.get_width(),merged_layer.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', merged_layer)
        config.set_property('add-alpha', True)
        result = procedure.run(config)
        median_blur_save = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_blur_save)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels-stretch')
        config = procedure.create_config()
        config.set_property('drawable', median_blur_save)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if play_through:
                if verbosity == 2:
                        print("  finished median blur")
                time.sleep(sleeptime)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(save_blurred_path))
                result = procedure.run(config)                

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_blur_save)
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
                config.set_property('fill-type', 1)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', black)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-flatten')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-export')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('file', Gio.file_new_for_path(blurred_path))
        result = procedure.run(config)

        if play_through:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-display-delete')
                config = procedure.create_config()
                config.set_property('display', display)
                result = procedure.run(config)
        else:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-image-delete')
                config = procedure.create_config()
                config.set_property('image', image)
                result = procedure.run(config)
         
        procedure = Gimp.get_pdb().lookup_procedure('gimp-quit')
        config = procedure.create_config()
        config.set_property('force', 1)
        result = procedure.run(config)

        '''image = pdb.file_fits_load(inpath, inpath)
        if play_through:
                pdb.gimp_display_new(image)
        pdb.gimp_image_convert_precision(image, 650)
        if play_through:
                time.sleep(sleeptime)
        original = image.active_layer
        pdb.gimp_layer_add_alpha(original)
        pdb.gimp_context_set_sample_threshold_int(0)
        pdb.gimp_image_select_color(image, 0, original, (0,0,0))
        pdb.gimp_drawable_edit_clear(original)
        original_copy = pdb.gimp_layer_copy(original, 0)
        pdb.gimp_image_insert_layer(image, original_copy, None, 0)
        pdb.gimp_selection_invert(image)
        if verbosity > 0:
                print(" gaussian blur...")
        pdb.python_gegl(image, original_copy, "gaussian-blur std-dev-x=2 std-dev-y=2 filter FIR")
        if play_through:
                time.sleep(sleeptime)
        if verbosity > 0:
                print(" wavelet decompose...")
        pdb.plug_in_wavelet_decompose(image, original_copy, 7, 1, 0)
        pdb.gimp_selection_none(image)
        freq1 = pdb.gimp_image_get_layer_by_name(image, 'Scale 1')
        freq2 = pdb.gimp_image_get_layer_by_name(image, 'Scale 2')
        freq3 = pdb.gimp_image_get_layer_by_name(image, 'Scale 3')
        freq4 = pdb.gimp_image_get_layer_by_name(image, 'Scale 4')
        freq5 = pdb.gimp_image_get_layer_by_name(image, 'Scale 5')
        freq6 = pdb.gimp_image_get_layer_by_name(image, 'Scale 6')
        freq7 = pdb.gimp_image_get_layer_by_name(image, 'Scale 7')
        residual = pdb.gimp_image_get_layer_by_name(image, 'Residual')
        pdb.gimp_item_set_visible(residual, 0)
        pdb.gimp_item_set_visible(freq7, 0)
        pdb.gimp_item_set_visible(freq6, 0)
        pdb.gimp_item_set_visible(freq5, 0)
        pdb.gimp_item_set_visible(freq4, 0)
        pdb.gimp_item_set_visible(freq3, 0)
        pdb.gimp_item_set_visible(freq2, 0)
        pdb.gimp_item_set_visible(freq1, 0)
        pdb.gimp_item_set_visible(residual, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(freq7, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(freq6, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        lowpass = pdb.gimp_layer_new_from_visible(image, image, 'Lowpass')
        pdb.gimp_image_insert_layer(image, lowpass, None, 1)
        pdb.gimp_item_set_visible(residual, 0)
        pdb.gimp_item_set_visible(freq7, 0)
        pdb.gimp_item_set_visible(freq6, 0)
        pdb.gimp_item_set_visible(freq1, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(freq2, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(freq3, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        highpass = pdb.gimp_layer_new_from_visible(image, image, 'Highpass')
        pdb.gimp_image_insert_layer(image, highpass, None, 1)
        decomposition = pdb.gimp_image_get_layer_by_name(image, 'Decomposition')
        pdb.gimp_image_remove_layer(image, decomposition)
        if verbosity > 0:
                print(" thresholding & masking...")
        mean, std_dev, median, pixels, count, percentile = pdb.gimp_drawable_histogram(highpass, 0, 0, 1)
        high_thresh = mean + 4*std_dev
        pdb.gimp_drawable_threshold(highpass, 0, high_thresh, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(lowpass, 0)
        pdb.gimp_item_set_visible(original_copy, 0)
        highpass_mask = pdb.gimp_layer_create_mask(highpass, 5)
        pdb.gimp_layer_add_mask(highpass, highpass_mask)
        pdb.gimp_image_select_item(image, 0, highpass_mask)
        pdb.gimp_selection_grow(image, 5)
        pdb.gimp_selection_flood(image)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(highpass, 0)
        pdb.gimp_drawable_edit_clear(original)
        pdb.gimp_selection_none(image)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(lowpass, 1)
        pdb.gimp_displays_flush()
        mean, std_dev, median, pixels, count, percentile = pdb.gimp_drawable_histogram(lowpass, 0, 0, 1)
        low_thresh = mean + 1.5*std_dev
        pdb.gimp_drawable_threshold(lowpass, 0, low_thresh, 1)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        lowpass_mask = pdb.gimp_layer_create_mask(lowpass, 5)
        pdb.gimp_layer_add_mask(lowpass, lowpass_mask)
        pdb.gimp_image_select_item(image, 0, lowpass_mask)
        pdb.gimp_selection_grow(image, 10)
        pdb.gimp_selection_flood(image)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        pdb.gimp_item_set_visible(lowpass, 0)
        pdb.gimp_drawable_edit_clear(original)
        pdb.gimp_selection_none(image)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        if verbosity > 0:
                print(" filling mask...")
        mean, std_dev, median, pixels, count, percentile = pdb.gimp_drawable_histogram(original, 0, 0, 1)
        pdb.gimp_context_set_foreground((median,median,median))
        height = pdb.gimp_image_height(image)
        width = pdb.gimp_image_width(image)
        bgfill = pdb.gimp_layer_new(image, width, height, 2, 'BGfill', 100, 0)
        pdb.gimp_image_insert_layer(image, bgfill, None, 4)
        pdb.gimp_drawable_edit_bucket_fill(bgfill, 0, 1, 1)
        pdb.plug_in_rgb_noise(image, bgfill, 0, 0, std_dev*2, 0, 0, 0)
        merged = pdb.gimp_image_merge_down(image, original, 0)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
        if verbosity > 0:
                print(" median filtering...")
        pdb.python_gegl(image, merged, "median-blur radius=%i percentile=50 high-precision=1" %medblur_rad)
        if play_through:
                merged_copy = pdb.gimp_layer_copy(merged, 0)
                pdb.gimp_image_insert_layer(image, merged_copy, None, 0)
                pdb.gimp_drawable_levels_stretch(merged_copy)
        pdb.gimp_displays_flush()
        if play_through:
                time.sleep(sleeptime)
                pdb.gimp_item_set_visible(merged_copy, 0)
        export_layer = pdb.gimp_image_flatten(image)
        pdb.gimp_layer_flatten(export_layer)
        if verbosity > 0:
                print(" saving & exiting gimp...")
        pdb.file_fits_save(image, export_layer, outpath, outpath)
        if not play_through:
                pdb.gimp_image_delete(image)              
        pdb.gimp_quit(1)'''
