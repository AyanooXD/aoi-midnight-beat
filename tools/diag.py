"""Silhouette diagnostic: is the subject actually in frame, and how big?"""
import bpy
import os
import numpy as np
from PIL import Image
from mathutils import Vector


def silhouette(cam, path, res=(400, 560), target=(0, 0, 0.86), dist=5.0,
               lens=85, ortho=None, yaw=0.0, pitch=0.0):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.view_settings.view_transform = 'Standard'
    sc.display.shading.light = 'FLAT'
    sc.display.shading.color_type = 'SINGLE'
    sc.display.shading.single_color = (1, 1, 1)
    sc.display.shading.show_shadows = False
    sc.display.shading.show_cavity = False
    sc.display.shading.show_specular_highlight = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'

    import math
    y, p = math.radians(yaw), math.radians(pitch)
    cam.location = (math.sin(y) * math.cos(p) * dist,
                    -math.cos(y) * math.cos(p) * dist,
                    target[2] + math.sin(p) * dist)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'

    fl = bpy.data.objects.get("StudioFloor")
    if fl:
        fl.hide_render = True
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if fl:
        fl.hide_render = False
    sc.render.film_transparent = False

    a = np.asarray(Image.open(path).convert('RGBA'))
    al = a[:, :, 3]
    cov = float((al > 10).mean())
    ys, xs = np.where(al > 10)
    if len(xs) == 0:
        print("  %-28s EMPTY FRAME" % os.path.basename(path))
        return 0.0, None
    bb = (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    print("  %-28s coverage %5.1f%%  bbox x[%3d..%3d] y[%3d..%3d]  fills %4.0f%% x %4.0f%%"
          % (os.path.basename(path), 100 * cov, bb[0], bb[1], bb[2], bb[3],
             100 * (bb[1] - bb[0]) / res[0], 100 * (bb[3] - bb[2]) / res[1]))
    return cov, bb
