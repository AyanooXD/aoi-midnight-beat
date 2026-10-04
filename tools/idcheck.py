"""Object-ID diagnostic: render a unique flat colour per object, then decode
which object actually covers which pixels. Definitive, no guessing."""
import bpy
import os
import numpy as np
from PIL import Image
from collections import defaultdict
from mathutils import Vector


def id_colors(n):
    """Deterministic, visually separable RGB triples."""
    cols = []
    i = 1
    while len(cols) < n:
        r = (i * 97) % 255
        g = (i * 151) % 255
        b = (i * 211) % 255
        if r > 25 and g > 25 and b > 25:
            cols.append((r, g, b))
        i += 1
    return cols


def render_ids(cam, path, res=(400, 560), target=(0, 0, 0.86), dist=5.0,
               lens=85, ortho=None, yaw=0.0, pitch=0.0, hide=("StudioFloor",)):
    import math
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.view_settings.view_transform = 'Standard'
    sh = sc.display.shading
    sh.light = 'FLAT'
    sh.color_type = 'MATERIAL'
    sh.show_shadows = False
    sh.show_cavity = False
    sh.show_specular_highlight = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'

    y, p = math.radians(yaw), math.radians(pitch)
    cam.location = (math.sin(y) * math.cos(p) * dist,
                    -math.cos(y) * math.cos(p) * dist,
                    target[2] + math.sin(p) * dist)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        cam.data.ortho_scale = ortho

    meshes = [o for o in sc.objects if o.type == 'MESH' and o.name not in hide]
    meshes.sort(key=lambda o: o.name)
    cols = id_colors(len(meshes))

    saved = []
    idmats = []
    for i, o in enumerate(meshes):
        saved.append((o, list(o.data.materials)))
        m = bpy.data.materials.new("ID_" + o.name)
        m.use_nodes = True
        # Workbench reads the viewport display colour, not the shader graph.
        m.diffuse_color = (*cols[i], 1.0)
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*cols[i], 1.0)
        o.data.materials.clear()
        o.data.materials.append(m)
        idmats.append(m)

    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

    for o, mats in saved:
        o.data.materials.clear()
        for m in mats:
            o.data.materials.append(m)
    for m in idmats:
        bpy.data.materials.remove(m)
    sc.render.film_transparent = False

    a = np.asarray(Image.open(path).convert('RGBA')).astype(int)
    alpha = a[:, :, 3]
    rgb = a[:, :, :3]
    total = float((alpha > 10).sum())
    cov = defaultdict(int)
    for i, o in enumerate(meshes):
        c = cols[i]
        m = (np.abs(rgb - np.array(c)).sum(2) < 24) & (alpha > 10)
        if m.sum():
            cov[o.name] = int(m.sum())
    print("  frame '%s': %.1f%% covered, %d objects visible"
          % (os.path.basename(path), 100 * total / (res[0] * res[1]), len(cov)))
    for name, n in sorted(cov.items(), key=lambda kv: -kv[1])[:14]:
        print("      %-22s %6.2f%% of frame" % (name, 100 * n / (res[0] * res[1])))
    return cov, total / (res[0] * res[1])
