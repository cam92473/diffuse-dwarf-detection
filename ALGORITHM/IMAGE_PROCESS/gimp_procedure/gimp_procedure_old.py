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
    >> pick NaN color from border and store as foreground color
    >> crop away NaN border
    >> select non-NaN region and save it as a channel
    >> optionally, create a copy of the original layer, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> load the weight image as a layer up front (deal with it later)
    >> create a copy of the original layer to be blurred
    >> get median color of the non-NaN region and set it as the background color
    >> if the inverse of the non-NaN region exists (is not an empty selection), fill those NaNs with the median color (to prevent NaN bleeding when blurring) in the copy layer
    >> gaussian blur the copy of the original layer. This layer will be used for building a mask (the noise reduction of the Gaussian blur helps with shape recognition)
    >> create a copy of the original layer to mask objects in
    >> for reasons that have to do with a bug with thresholding in Gimp, convert image to perceptual lighting
    >> create a copy of the blurred layer, run a highpass filter on it, and threshold it according to its intensity stats (obtained via histogram)
    >> create a mask from this thresholded layer, flood and grow the mask, and then apply it to the masked layer. This masks out small objects.
    >> create a copy of the blurred layer, run a sobel edge-detection filter on it, and threshold it according to its intensity stats (obtained via histogram)
    >> a small corrective step has to be done at this point to remove a white border from the edge of the image
    >> create a mask from this thresholded layer, flood and grow the mask, and then apply it to the masked layer. This masks out medium objects.
    >> create a copy of the blurred layer, run a large gaussian blur on it, and threshold it according to its intensity stats (obtained via histogram)
    >> create a mask from this thresholded layer, flood and grow the mask, and then apply it to the masked layer. This masks out medium-large objects.
    >> create a copy of the blurred layer, run the "bloom" operation and adjust shadows, and threshold it according to its intensity stats (obtained via histogram)
    >> create a mask from this thresholded layer, flood the mask, and then apply it to the masked layer. This masks out large objects.
    >> create a copy of the blurred layer and threshold it at a high intensity value (to get a map of the brightest objects)
    >> create a copy of the blurred layer, run the unsharp mask filter on it, and threshold it according to its intensity stats (obtained via histogram). This provides a map showing the full extent of objects (a deep map) which doesn't suffer from overlap issues between potential dwarfs and stars.
    >> fill in holes in the deep map, then set its opacity to 75% to expose the bright map layer underneath. This results in a map showing the overlap states between the bright areas and the full extent of objects.
    >> merge the two layers, then select bright regions in the overlap states map. Acquire their centroids, and apply the fuzzy select tool with a low sample threshold to these centroids, which selects the full extent of only objects that contain bright pixels.
    >> create a mask from this selection, flood and grow the mask, and then apply it to the masked layer. This masks out extended objects (or more precisely, the full extent of the brightest objects).
    >> convert image back to linear lighting
    >> create a background layer and fill it with the median color of the masked layer. Apply noise.
    >> scale the weight layer according to how powerful you want the weighting to be
    >> copy the weight layer, copy the masked layer, apply the mask to the copied weight layer, and multiply the copied mask layer by the copied (and masked) weight layer, thereby applying the weight. Merge the two layers.
    >> copy the weight layer again, mask out the star weights by applying the sobel mask, and run a median filter with a maxed out alpha threshold to sew up as many holes as possible (while preserving banding, etc.)
    >> run a very large box blur on the original weight layer, and merge the two weight layers together, filling any remaining holes
    >> multiply the background by the merged weight layer and merge them
    >> finally, merge the weighted background with the weighted masked layer, creating a masked, weighted and filled layer, ready for median filtering
    >> optionally, create a copy of the masked, weighted and filled layer, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> create a copy of the masked, weighted and filled layer
    >> median filter this copied layer with a circular kernel with a radius specified by the user
    >> optionally, create a copy of this median-blurred layer copy, scale intensity levels, and save it as a jpeg (delete this layer afterward)
    >> if the NaN region in the median-blurred layer is not empty (exists), fill it with the foreground NaN color
    >> set the foreground color to black (for Gimp bug reasons) and flatten the image (remove the alpha channel)
    >> export the image as a fits file to a directory labelled ("blurred")
    >> delete display and image and exit Gimp

"""

def gimp_procedure(data_file,weight_file,processed_file,save_dir,medblur_radius,save,play_through,signature,verbosity):
        sleeptime = 1

        ### opening image, setting foreground color to nan, and cropping away border nans ###

        if verbosity > 0:
                print("   loading and preparing images...")

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-load')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('file', Gio.file_new_for_path(data_file))
        result = procedure.run(config)
        image = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-display-new')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        display = result.index(1)

        original = image.get_layers()[0]

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', original)
        config.set_property('name', 'original')
        result = procedure.run(config)

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

        ### saving non-edge-nans as a channel ###

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

        if verbosity == 2:
                print("    data loaded and ready")

        if play_through:
                time.sleep(sleeptime)

        ### convert precision to linear if not already ###

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

        ### copy original layer, scale intensity levels, save as jpeg (if desired), then delete the layer ###

        if verbosity == 2:
                print("    saving scaled copy of original layer as jpeg...")

        if play_through:
                time.sleep(sleeptime)

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
        config.set_property('low-input', max(0,median-0.015))
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

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_dir)/f'{signature}_A_data.jpeg')))
                result = procedure.run(config)

        if verbosity == 2:
                print("    file saved successfully")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_save)
        result = procedure.run(config)

        ### load weight layer up front to avoid crashing later (for very large images) ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-file-load-layer')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('file', Gio.file_new_for_path(weight_file))
        result = procedure.run(config)
        weight = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', weight)
        config.set_property('parent', None)
        config.set_property('position', -1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', weight)
        config.set_property('name', 'weight')
        result = procedure.run(config)

        if verbosity == 2:
                print("    weight loaded")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight)
        config.set_property('visible', False)
        result = procedure.run(config)

        ### copy original layer to a new layer (that will be blurred) and prepare it for blurring by setting edge nans (if they exist) to the median color ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        blurred = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', blurred)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', blurred)
        config.set_property('name', 'blurred')
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
                config.set_property('drawable', blurred)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        ### convert colorspace to perceptual in preparation for thresholding ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('precision', 650)
        result = procedure.run(config)

        ### apply gaussian blur of std. 2.5 ###

        if verbosity > 0:
                print("   Gaussian blur...")

        Gegl.init()

        buffer = blurred.get_buffer()
        shadow = blurred.get_shadow_buffer()
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
        blurred.merge_shadow(True)
        blurred.update(0,0,blurred.get_width(),blurred.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    Gaussian blurred layer ready")

        if play_through:
                time.sleep(sleeptime)

        ### create a copy of original layer (masked) in which to mask objects, and set visibility of blurred and original layers to False

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        original_masked = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_masked)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', original_masked)
        config.set_property('name', 'original_masked')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', original)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', blurred)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    masked layer ready")

        if play_through:
                time.sleep(sleeptime)

        ### create a copy of blurred layer, run highpass filter, and threshold (to get a mask for small objects), then apply mask to original_masked layer ###

        if verbosity > 0:
                print("   highpass masking...")

        if verbosity == 2:
                print("    running highpass filter...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        highpass = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', highpass)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', highpass)
        config.set_property('name', 'highpass')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', highpass)
        config.set_property('visible', True)
        result = procedure.run(config)

        Gegl.init()

        buffer = highpass.get_buffer()
        shadow = highpass.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        hp = graph.create_child("gegl:high-pass")
        hp.set_property("std-dev",2)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(hp)
        hp.link(write)
        write.process()
        shadow.flush()
        highpass.merge_shadow(True)
        highpass.update(0,0,highpass.get_width(),highpass.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and getting mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', highpass)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        highpass_thresh = mean + std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', highpass)
        config.set_property('channel', 0)
        config.set_property('low-threshold', highpass_thresh)
        config.set_property('high-threshold', 1)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    applying mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 2)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### create a copy of blurred layer, run sobel edge-detection filter, and threshold (to get a mask for medium objects), then apply mask to original_masked layer ###

        if verbosity > 0:
                print("   Sobel masking...")

        if verbosity == 2:
                print("    running Sobel edge-detection...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        sobel = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', sobel)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', sobel)
        config.set_property('name', 'sobel')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', sobel)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('plug-in-edge')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('drawable', sobel)
        config.set_property('amount', 1)
        config.set_property('edgemode', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and getting mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', sobel)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        sobel_thresh = mean + std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', sobel)
        config.set_property('channel', 0)
        config.set_property('low-threshold', sobel_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        ### getting the border pixels and setting them to "black" (actually transparency), an extra step that's needed for sobel (which whitens pixels on the image border) ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-all')
        config = procedure.create_config(); config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-shrink')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
        config = procedure.create_config()
        config.set_property('drawable', sobel)
        config.set_property('fill-type', 4)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        ### extra step complete ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', sobel)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        sobel_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', sobel)
        config.set_property('mask', sobel_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', sobel_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    applying mask...")

        if play_through:
                time.sleep(sleeptime)

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
        config.set_property('item', sobel)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### create a copy of blurred layer, run a large gaussian blur, and threshold (to get a mask for medium-large objects), then apply mask to original_masked layer ###

        '''
        if verbosity > 0:
                print("   Gaussian masking...")

        if verbosity == 2:
                print("    running large gaussian blur...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        largegauss = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', largegauss)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', largegauss)
        config.set_property('name', 'largegauss')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', largegauss)
        config.set_property('visible', True)
        result = procedure.run(config)

        Gegl.init()

        buffer = largegauss.get_buffer()
        shadow = largegauss.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        gauss = graph.create_child("gegl:gaussian-blur")
        #12.5
        gauss.set_property("std-dev-x",30)
        gauss.set_property("std-dev-y",30)
        gauss.set_property("filter",'FIR')
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(gauss)
        gauss.link(write)
        write.process()
        shadow.flush()
        largegauss.merge_shadow(True)
        largegauss.update(0,0,largegauss.get_width(),largegauss.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and getting mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', largegauss)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        largegauss_thresh = mean + 3*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', largegauss)
        config.set_property('channel', 0)
        config.set_property('low-threshold', largegauss_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', largegauss)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        largegauss_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', largegauss)
        config.set_property('mask', largegauss_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', largegauss_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    applying mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 2)
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
        config.set_property('item', largegauss)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)'''

        ### difference of Gaussians

        if verbosity > 0:
                print("   difference of Gaussians masking...")

        if verbosity == 2:
                print("    running difference-of-Gaussians filter...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        dog = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', dog)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', dog)
        config.set_property('name', 'dog')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', dog)
        config.set_property('visible', True)
        result = procedure.run(config)

        Gegl.init()

        buffer = dog.get_buffer()
        shadow = dog.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        diff = graph.create_child("gegl:difference-of-gaussians")
        diff.set_property("radius1",30)
        diff.set_property("radius2",5)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(diff)
        diff.link(write)
        write.process()
        shadow.flush()
        dog.merge_shadow(True)
        dog.update(0,0,dog.get_width(),dog.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and getting mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', dog)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        dog_thresh = mean + 1.5*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', dog)
        config.set_property('channel', 0)
        config.set_property('low-threshold', dog_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', dog)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        dog_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', dog)
        config.set_property('mask', dog_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', dog_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    applying mask...")

        if play_through:
                time.sleep(sleeptime)

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
        config.set_property('item', dog)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### create a copy of blurred layer, use the bloom tool, adjust the shadows, and threshold (to get a mask for large objects), then apply mask to original_masked layer ###

        '''
        if verbosity > 0:
                print("   Bloom&Shadow masking...")

        if verbosity == 2:
                print("    running Bloom filter...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        bloom = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', bloom)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', bloom)
        config.set_property('name', 'bloom')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', bloom)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', bloom)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        Gegl.init()

        buffer = bloom.get_buffer()
        shadow = bloom.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        bl = graph.create_child("gegl:bloom")
        bl.set_property("threshold",100*(mean-0.1*std_dev))
        bl.set_property("softness",0)
        bl.set_property("radius",15)
        bl.set_property("strength",100)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(bl)
        bl.link(write)
        write.process()
        shadow.flush()
        bloom.merge_shadow(True)
        bloom.update(0,0,bloom.get_width(),bloom.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    adjusting Shadows...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-shadows-highlights')
        config = procedure.create_config()
        config.set_property('drawable', bloom)
        config.set_property('shadows', -100)
        config.set_property('highlights', 0)
        config.set_property('whitepoint', 0)
        config.set_property('radius', 100)
        config.set_property('compress', 50)
        config.set_property('shadows-ccorrect', 100)
        config.set_property('highlights-ccorrect', 50)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and getting mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', bloom)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        bloom_thresh = mean + 1.8*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', bloom)
        config.set_property('channel', 0)
        config.set_property('low-threshold', bloom_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', bloom)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        bloom_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', bloom)
        config.set_property('mask', bloom_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', bloom_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    applying mask...")

        if play_through:
                time.sleep(sleeptime)

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
        config.set_property('item', bloom)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)'''

        ### create a copy of blurred layer, threshold at a high intensity, and erode the result 3 times (to get a mask for the brightest objects) ###

        '''if verbosity > 0:
                print("   deep masking...")

        if verbosity == 2:
                print("    thresholding to get brightest pixels...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        bright = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', bright)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', bright)
        config.set_property('name', 'bright')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', bright)
        config.set_property('visible', True)
        result = procedure.run(config)

        bright_thresh = 0.95
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', bright)
        config.set_property('channel', 0)
        config.set_property('low-threshold', bright_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        '''

        '''for _ in range(2):
                procedure = Gimp.get_pdb().lookup_procedure('plug-in-erode')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('drawable', bright)
                config.set_property('propagate-mode',0)
                config.set_property('lower-limit', 0)
                config.set_property('upper-limit', 255)
                result = procedure.run(config)

        for _ in range(4):
                procedure = Gimp.get_pdb().lookup_procedure('plug-in-dilate')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('drawable', bright)
                config.set_property('propagate-mode',0)
                config.set_property('lower-limit', 0)
                config.set_property('upper-limit', 255)
                result = procedure.run(config)'''
                
        '''

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### create a copy of blurred layer, apply unsharp mask, and threshold (to get a map that shows extended objects, but does not suffer from connectivity with bright stars) ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', blurred)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        unsharp = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', unsharp)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', unsharp)
        config.set_property('name', 'unsharp')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', unsharp)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    running Unsharp mask on another copy...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('plug-in-unsharp-mask')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('drawable', unsharp)
        config.set_property('radius', 3)
        config.set_property('amount', 5)
        result = procedure.run(config)

        #15,0.5

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and filling in holes...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', unsharp)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)
        median = result.index(3)

        unsharp_thresh = median + 0.15*std_dev
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', unsharp)
        config.set_property('channel', 0)
        config.set_property('low-threshold', unsharp_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### fill in holes in the extended objects by selecting all objects, trimming away noisy fluff by shrinking the selection, and flooding ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-color')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('drawable', unsharp)
        config.set_property('color', white_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-shrink')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 5)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
        config = procedure.create_config()
        config.set_property('drawable', unsharp)
        config.set_property('fill-type', 3)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### set the opacity of the extended objects map to 75%, showing the bright objects map underneath. Merge the two layers to get a map of the overlap states between the bright objects and extended objects ###

        if verbosity == 2:
                print("    combining unsharp and bright layers...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-set-opacity')
        config = procedure.create_config()
        config.set_property('layer', unsharp)
        config.set_property('opacity', 75)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', unsharp)
        result = procedure.run(config)
        deep = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', deep)
        config.set_property('name', 'deep')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### take the bright regions, compile their centroids into a list of points, and iterate through the points, applying the fuzzy select tool with a lowered sample threshold to select the extended objects that have bright pixels in them. This becomes a mask for the extended objects, which is applied to the masked layer ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-color')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('drawable', deep)
        config.set_property('color', white_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-is-empty')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        is_empty = result.index(1)

        if verbosity == 2:
                print("    getting coordinates of white objects...")

        if play_through:
                time.sleep(sleeptime)

        if not is_empty:
                procedure = Gimp.get_pdb().lookup_procedure('plug-in-sel2path')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('num-drawables', 1)
                config.set_property('drawables', Gimp.ObjectArray.new(Gimp.Drawable, [deep], False))
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-image-get-vectors')
                config = procedure.create_config()
                config.set_property('image', image)
                result = procedure.run(config)
                vectors = result.index(2)
                #
                vector = vectors.data[0]
                srcpoints = []
                for stroke in vector.get_strokes():
                        pnts = vector.stroke_get_points(stroke).controlpoints
                        x = pnts[::2]
                        y = pnts[1::2]
                        avgx = sum(x)/len(x)
                        avgy = sum(y)/len(y)
                        srcpoints.append((avgx,avgy))
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-sample-threshold-int')
                config = procedure.create_config()
                config.set_property('sample-threshold', 50)
                result = procedure.run(config)
                #
                if verbosity == 2:
                        print("    selecting and flooding coordinates...")
                #
                if play_through:
                        time.sleep(sleeptime)
                #
                for pnt in srcpoints:
                        x = pnt[0]
                        y = pnt[1]
                        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-contiguous-color')
                        config = procedure.create_config()
                        config.set_property('image', image)
                        config.set_property('operation', 0)
                        config.set_property('drawable', deep)
                        config.set_property('x', x)
                        config.set_property('y', y)
                        result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', deep)
                config.set_property('fill-type', 3)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-sample-threshold-int')
                config = procedure.create_config()
                config.set_property('sample-threshold', 0)
                result = procedure.run(config)
                #
                if verbosity == 2:
                        print("    getting mask...")
                #
                if play_through:
                        time.sleep(sleeptime)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
                config = procedure.create_config()
                config.set_property('layer', deep)
                config.set_property('mask-type', 4)
                result = procedure.run(config)
                deep_mask = result.index(1)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
                config = procedure.create_config()
                config.set_property('layer', deep)
                config.set_property('mask', deep_mask)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
                config = procedure.create_config()
                config.set_property('image', image)
                config.set_property('operation', 2)
                config.set_property('item', deep_mask)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)
                #
                if verbosity == 2:
                        print("    applying mask...")
                #
                if play_through:
                        time.sleep(sleeptime)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
                config = procedure.create_config()
                config.set_property('image', image)
                config.set_property('steps', 10)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-flood')
                config = procedure.create_config()
                config.set_property('image', image)
                result = procedure.run(config)      
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
                config = procedure.create_config()
                config.set_property('item', deep)
                config.set_property('visible', False)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
                config = procedure.create_config()
                config.set_property('drawable', original_masked)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
                config = procedure.create_config()
                config.set_property('image', image)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)
        else:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
                config = procedure.create_config()
                config.set_property('item', deep)
                config.set_property('visible', False)
                result = procedure.run(config)
                #
                procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
                config = procedure.create_config()
                result = procedure.run(config)'''   

        ### make slight improvements to the mask of the masked image ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', original_masked)
        config.set_property('mask-type', 2)
        result = procedure.run(config)
        om_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', original_masked)
        config.set_property('mask', om_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', om_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-grow')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('steps', 2)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-remove-mask')
        config = procedure.create_config()
        config.set_property('layer', original_masked)
        config.set_property('mode', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### remove erroneous partly-transparent places in image, if any exist (by making them completely opaque) ###

        procedure = Gimp.get_pdb().lookup_procedure('plug-in-threshold-alpha')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('drawable', original_masked)
        config.set_property('threshold', 0.1)
        result = procedure.run(config)        

        ### convert precision back to linear ###

        if verbosity > 0:
                print("   converting precision to linear...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('precision', 600)
        result = procedure.run(config)

        ### create a background layer and fill it with the median color of the masked layer ###

        if verbosity > 0:
                print("   making background...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', original_masked)
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

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', original_masked)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-new')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('width', image.get_width())
        config.set_property('height', image.get_height())
        config.set_property('type', 2)
        config.set_property('name', 'background')
        config.set_property('opacity', 100)
        result = procedure.run(config)
        background = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', background)
        config.set_property('parent', None)
        config.set_property('position', 6)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', background)
        config.set_property('name', 'background')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-bucket-fill')
        config = procedure.create_config()
        config.set_property('drawable', background)
        config.set_property('fill-type', 1)
        config.set_property('x', 0)
        config.set_property('y', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    adding noise...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('plug-in-rgb-noise')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('drawable', background)
        config.set_property('independent', 0)
        config.set_property('correlated', 0)
        config.set_property('noise-1', std_dev*1.75)
        config.set_property('noise-2', 0)
        config.set_property('noise-3', 0)
        config.set_property('noise-4', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### reorder weight layer and scale intensity levels ###

        if verbosity > 0:
                print("   applying weight...")

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-reorder-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('item', weight)
        config.set_property('parent', None)
        config.set_property('position', 7)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', background)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', white_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', black)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-is-empty')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)
        is_empty = result.index(1)

        if not is_empty:
                procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-fill')
                config = procedure.create_config()
                config.set_property('drawable', weight)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', white_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', median_masked_color)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    scaling weight appropriately...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels')
        config = procedure.create_config()
        config.set_property('drawable', weight)
        config.set_property('channel', 0)
        config.set_property('low-input', 0)
        config.set_property('high-input', 1)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0.95) #0.95
        config.set_property('high-output', 1)
        result = procedure.run(config)

        ### copy weight layer, copy masked layer, apply the mask to the copied weight layer, then multiply the copied masked layer by the copied weight layer and merge the two ###

        if verbosity == 2:
                print("    weighting masked layer...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', weight)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        weight_copy = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', weight_copy)
        config.set_property('parent', None)
        config.set_property('position', 6)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', weight_copy)
        config.set_property('name', 'weight_copy')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original_masked)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        original_masked_weighted = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', original_masked_weighted)
        config.set_property('parent', None)
        config.set_property('position', 6)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted)
        config.set_property('name', 'original_masked_weighted')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', original_masked)
        config.set_property('mask-type', 2)
        result = procedure.run(config)
        alpha_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', original_masked)
        config.set_property('mask', alpha_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', alpha_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', weight_copy)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-set-mode')
        config = procedure.create_config()
        config.set_property('layer', original_masked_weighted)
        config.set_property('mode', 30)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', original_masked_weighted)
        config.set_property('merge-type', 0)
        result = procedure.run(config)
        original_masked_weighted = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted)
        config.set_property('name', 'original_masked_weighted')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### copy the weight layer once again and apply the sobel mask to it to remove the weights of bright stars. Then median blur the weight layer with a maxed alpha threshold to remove as many holes as possible while preserving edges (banding) ###

        if verbosity == 2:
                print("    weighting background...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', weight)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        weight_masked = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', weight_masked)
        config.set_property('parent', None)
        config.set_property('position', 8)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', weight_masked)
        config.set_property('name', 'weight_masked')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', sobel_mask)
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
        config.set_property('item', weight)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', weight_masked)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', weight_masked)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        median_weight = result.index(3)

        median_weight_color = Gegl.Color()
        median_weight_color.set_rgba(median_weight,median_weight,median_weight,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', median_weight_color)
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
                config.set_property('drawable', weight_masked)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        Gegl.init()

        buffer = weight_masked.get_buffer()
        shadow = weight_masked.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        mb = graph.create_child("gegl:median-blur")
        mb.set_property("neighborhood",'Square')
        mb.set_property("radius",20)
        mb.set_property("alpha-percentile",100)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(mb)
        mb.link(write)
        write.process()
        shadow.flush()
        weight_masked.merge_shadow(True)
        weight_masked.update(0,0,weight_masked.get_width(),weight_masked.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', black)
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
                config.set_property('drawable', weight_masked)
                config.set_property('fill-type', 1)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-invert')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        median_masked_color.set_rgba(median_masked*0.95,median_masked*0.95,median_masked*0.95,1.)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-background')
        config = procedure.create_config()
        config.set_property('background', median_masked_color)
        result = procedure.run(config)

        ### run a very large box blur on the original weight layer, and then merge the two weight layers, thus filling in any remaining holes

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight_masked)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        Gegl.init()

        buffer = weight.get_buffer()
        shadow = weight.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        bb = graph.create_child("gegl:box-blur")
        bb.set_property("radius",50)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(bb)
        bb.link(write)
        write.process()
        shadow.flush()
        weight.merge_shadow(True)
        weight.update(0,0,weight.get_width(),weight.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', weight_masked)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', weight_masked)
        config.set_property('merge-type', 0)
        result = procedure.run(config)
        merged_weight = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### multiply the background with the merged weight layer and merge ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', background)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-set-mode')
        config = procedure.create_config()
        config.set_property('layer', background)
        config.set_property('mode', 30)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', background)
        config.set_property('merge-type', 0)
        result = procedure.run(config)
        background_weighted = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', background_weighted)
        config.set_property('name', 'background_weighted')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### now merge the weighted background with the weighted masked layer to get the weighted, masked and filled layer, which is finally ready for median filtering. ###

        if verbosity == 2:
                print("    merging weighted background with weighted masked layer...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', background_weighted)
        config.set_property('add-alpha', 1)
        result = procedure.run(config)
        background_weighted_copy = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', background_weighted_copy)
        config.set_property('parent', None)
        config.set_property('position', -1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', background_weighted_copy)
        config.set_property('name', 'background_weighted_copy')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', background_weighted)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', original_masked_weighted)
        config.set_property('merge-type', 0)
        result = procedure.run(config)
        original_masked_weighted_filled = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted_filled)
        config.set_property('name', 'original_masked_weighted_filled')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### perform a second high pass filtering on the masked and filled layer, to eliminate remaining stars

        if verbosity > 0:
                print("   highpass masking a second time...")

        if verbosity == 2:
                print("    running highpass filter...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original_masked_weighted_filled)
        result = procedure.run(config)
        omwf_hp = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', omwf_hp)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', omwf_hp)
        config.set_property('name', 'second_highpass')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels-stretch')
        config = procedure.create_config()
        config.set_property('drawable', omwf_hp)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('precision', 650)
        result = procedure.run(config)

        Gegl.init()

        buffer = omwf_hp.get_buffer()
        shadow = omwf_hp.get_shadow_buffer()
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
        omwf_hp.merge_shadow(True)
        omwf_hp.update(0,0,omwf_hp.get_width(),omwf_hp.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        Gegl.init()

        buffer = omwf_hp.get_buffer()
        shadow = omwf_hp.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        hp = graph.create_child("gegl:high-pass")
        hp.set_property("std-dev",12)
        hp.set_property("contrast",2)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(hp)
        hp.link(write)
        write.process()
        shadow.flush()
        omwf_hp.merge_shadow(True)
        omwf_hp.update(0,0,omwf_hp.get_width(),omwf_hp.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    thresholding and getting mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', omwf_hp)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        mean = result.index(1)
        std_dev = result.index(2)

        omwf_hp_thresh = mean + std_dev*3
        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-threshold')
        config = procedure.create_config()
        config.set_property('drawable', omwf_hp)
        config.set_property('channel', 0)
        config.set_property('low-threshold', omwf_hp_thresh)
        config.set_property('high-threshold', 1)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-create-mask')
        config = procedure.create_config()
        config.set_property('layer', omwf_hp)
        config.set_property('mask-type', 5)
        result = procedure.run(config)
        omwf_hp_mask = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-add-mask')
        config = procedure.create_config()
        config.set_property('layer', omwf_hp)
        config.set_property('mask', omwf_hp_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', omwf_hp_mask)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if verbosity == 2:
                print("    applying mask...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 3)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', omwf_hp)
        config.set_property('visible', False)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-edit-clear')
        config = procedure.create_config()
        config.set_property('drawable', original_masked_weighted_filled)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-selection-none')
        config = procedure.create_config()
        config.set_property('image', image)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', background_weighted)
        config.set_property('visible', True)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-merge-down')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('merge-layer', original_masked_weighted_filled)
        config.set_property('merge-type', 0)
        result = procedure.run(config)
        original_masked_weighted_filled_complete = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted_filled_complete)
        config.set_property('name', 'original_masked_weighted_filled_complete')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-convert-precision')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('precision', 600)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### copy the weighted, masked, filled layer, scale intensity levels, save as jpeg (if desired), then delete the layer ###

        if verbosity == 2:
                print("    saving scaled copy of masked layer as jpeg...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original_masked_weighted_filled_complete)
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
        config.set_property('low-input', median_masked-0.01)
        config.set_property('high-input', median_masked+0.01)
        config.set_property('clamp-input', False)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0)
        config.set_property('high-output', 1)
        config.set_property('clamp-output', False)
        result = procedure.run(config) 

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_dir)/f'{signature}_B_masked.jpeg')))
                result = procedure.run(config)

        if verbosity == 2:
                print("    file saved successfully")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', masked_save)
        result = procedure.run(config)

        ### median filter the masked image to expose diffuse structures ###

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-select-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('operation', 2)
        config.set_property('item', nonnan_channel)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', original_masked_weighted_filled_complete)
        result = procedure.run(config)
        median_filtered = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_filtered)
        config.set_property('parent', None)
        config.set_property('position', 6)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-name')
        config = procedure.create_config()
        config.set_property('item', median_filtered)
        config.set_property('name', 'median_filtered')
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-item-set-visible')
        config = procedure.create_config()
        config.set_property('item', original_masked_weighted_filled_complete)
        config.set_property('visible', False)
        result = procedure.run(config)

        if verbosity > 0:
                print(f"   median filtering (kernel radius = {medblur_radius})...")

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
                config.set_property('drawable', median_filtered)
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

        buffer = median_filtered.get_buffer()
        shadow = median_filtered.get_shadow_buffer()
        graph = Gegl.Node()
        src = graph.create_child("gegl:buffer-source")
        src.set_property("buffer", buffer)
        median_filt = graph.create_child("gegl:median-blur")
        median_filt.set_property("radius",medblur_radius)
        median_filt.set_property("high-precision",True)
        write = graph.create_child("gegl:write-buffer")
        write.set_property("buffer", shadow)
        src.link(median_filt)
        median_filt.link(write)
        write.process()
        shadow.flush()
        median_filtered.merge_shadow(True)
        median_filtered.update(0,0,median_filtered.get_width(),median_filtered.get_height())

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        ### copy the median filtered layer, scale intensity levels, save as jpeg (if desired), then delete the layer ###

        if verbosity == 2:
                print("    saving scaled copy of median-filtered layer as jpeg...")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-histogram')
        config = procedure.create_config()
        config.set_property('drawable', median_filtered)
        config.set_property('channel', 0)
        config.set_property('start-range', 0)
        config.set_property('end-range', 1)
        result = procedure.run(config)
        std_dev = result.index(2)
        median = result.index(3)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-copy')
        config = procedure.create_config()
        config.set_property('layer', median_filtered)
        config.set_property('add-alpha', True)
        result = procedure.run(config)
        median_filtered_save = result.index(1)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-insert-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_filtered_save)
        config.set_property('parent', None)
        config.set_property('position', 0)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-drawable-levels')
        config = procedure.create_config(); config.set_property('drawable', median_filtered_save)
        config.set_property('channel', 0)
        config.set_property('low-input', median-0.005)
        config.set_property('high-input', median+0.005)
        config.set_property('clamp-input', False)
        config.set_property('gamma', 1)
        config.set_property('low-output', 0)
        config.set_property('high-output', 1)
        config.set_property('clamp-output', False)
        result = procedure.run(config) 

        procedure = Gimp.get_pdb().lookup_procedure('gimp-displays-flush')
        config = procedure.create_config()
        result = procedure.run(config)

        if save:
                procedure = Gimp.get_pdb().lookup_procedure('file-jpeg-export')
                config = procedure.create_config()
                config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
                config.set_property('image', image)
                config.set_property('file', Gio.file_new_for_path(str(Path(save_dir)/f'{signature}_C_processed.jpeg')))
                result = procedure.run(config) 

        if verbosity == 2:
                print("    file saved successfully")

        if play_through:
                time.sleep(sleeptime)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-reorder-item')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('item', median_filtered)
        config.set_property('parent', None)
        config.set_property('position', 1)
        result = procedure.run(config)               

        procedure = Gimp.get_pdb().lookup_procedure('gimp-image-remove-layer')
        config = procedure.create_config()
        config.set_property('image', image)
        config.set_property('layer', median_filtered_save)
        result = procedure.run(config)

        if verbosity > 0:
                print("   writing FITS file...")

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
                config.set_property('drawable', median_filtered)
                config.set_property('fill-type', 0)
                result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-context-set-foreground')
        config = procedure.create_config()
        config.set_property('foreground', black)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('gimp-layer-flatten')
        config = procedure.create_config()
        config.set_property('layer', median_filtered)
        result = procedure.run(config)

        procedure = Gimp.get_pdb().lookup_procedure('file-fits-export')
        config = procedure.create_config()
        config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
        config.set_property('image', image)
        config.set_property('file', Gio.file_new_for_path(processed_file))
        result = procedure.run(config)

        if verbosity > 0:
                print("   exiting GIMP...")

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
