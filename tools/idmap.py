"""Render a coarse MATERIAL-ID map + brightness map as text, to reason about
framing and part placement without an image viewer."""
import bpy
import os
import numpy as np
from PIL import Image
import math
from mathutils import Vector


PAL = [
    ("SKIN",   "#F7D4C8"),
    ("HAIR",   "#453F5C"),
    ("ACCENT", "#8B93F5"),
    ("WHITE",  "#F2EFF4"),
    ("DENIM",  "#4A5478"),
    ("METAL",  "#B9BCC9"),
    ("SHOE",   "#39405C"),
    ("FLOOR",  "#2B2E36"),
    ("DARK",   "#101218"),
]
# map the shader group names onto the palette entries above
GROUP2PAL = {
    "Skin": "SKIN", "Socket": "WHITE", "Eye": "DARK",
    "Hair": "HAIR", "Cloth_Outer": "DENIM", "Cloth_Trim": "ACCENT",
    "Cloth_Inner": "WHITE", "Denim": "DENIM", "Shoe": "SHOE",
    "Metal": "METAL", "Rubber": "DARK", "Face": "DARK",
    "Lash": "DARK", "LashLow": "DARK", "Brow": "DARK",
    "Unknown": "DARK",
}


def _hx(s):
    """sRGB hex -> LINEAR floats. Blender shader colour inputs are linear;
    feeding them sRGB values makes everything render far too bright."""
    s = s.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(s[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return np.array(out)


def _lin2srgb(c):
    c = np.asarray(c, np.float64)
    out = np.where(c <= 0.0031308, c * 12.92, 1.055 * np.maximum(c, 0) ** (1 / 2.4) - 0.055)
    return np.clip(out, 0, 1)


def id_render(cam, path, res=(44, 60), target=(0, 0, 0.86), dist=3.5, lens=85,
              ortho=None, yaw=0.0, pitch=0.0, hide=("StudioFloor",)):
    """Flat-shaded ID render, then quantise to the palette above."""
    import assemble
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

    grp = assemble.material_group_of
    meshes = [o for o in sc.objects if o.type == 'MESH' and o.name not in hide]
    saved = []
    for i, o in enumerate(meshes):
        g = GROUP2PAL.get(grp(o.name), "DARK")
        c = _hx(dict(PAL)[g])
        m = bpy.data.materials.new("IDX")
        m.use_nodes = True
        m.diffuse_color = (*c, 1.0)
        b = m.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = (*c, 1.0)
        o.data.materials.clear()
        o.data.materials.append(m)
        saved.append((o, list(o.data.materials)))
    fl = bpy.data.objects.get("StudioFloor")
    if fl:
        saved.append((fl, list(fl.data.materials)))
        fl.data.materials.clear()
        mf = bpy.data.materials.new("IDF")
        mf.use_nodes = True
        mf.diffuse_color = (*_hx(dict(PAL)["FLOOR"]), 1.0)
        b = mf.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = (*_hx(dict(PAL)["FLOOR"]), 1.0)
        fl.data.materials.append(mf)
    if fl:
        fl.hide_render = False

    hi = path.replace(".png", "_hi.png")
    sc.render.resolution_x, sc.render.resolution_y = (res[0] * 8, res[1] * 8)
    sc.render.filepath = hi
    bpy.ops.render.render(write_still=True)
    for o, mats in saved:
        o.data.materials.clear()
        for m in mats:
            o.data.materials.append(m)
    if fl:
        fl.hide_render = True
    sc.render.film_transparent = False

    a = np.asarray(Image.open(hi).convert('RGBA')).astype(np.float32) / 255.0
    small = np.asarray(Image.fromarray((a * 255).astype(np.uint8))
                       .resize((res[0], res[1]), Image.BOX), np.float32) / 255.0
    return small


def show(small, title, legend=PAL):
    rgb = small[:, :, :3]
    al = small[:, :, 3]
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    print("\n=== %s ===" % title)
    print("   " + "  ".join("%s=%s" % (n, c) for n, c in legend))
    P = np.stack([_hx(c) for _, c in legend])
    d = np.abs(rgb[:, :, None, :] - P[None, None, :, :]).sum(-1)
    idx = d.argmin(-1)
    for r in range(rgb.shape[0]):
        line = ""
        for c in range(rgb.shape[1]):
            if al[r, c] < 0.5:
                line += " "
            else:
                n = legend[idx[r, c]][0]
                line += n[0] + n[1:].lower()
        print("   |" + line + "|")
    RAMP = "@%#*+=-:. "
    print("   brightness (linear -> sRGB):")
    for r in range(rgb.shape[0]):
        print("   |" + "".join(
            " " if al[r, c] < 0.5 else RAMP[min(9, int(_lin2srgb(lum[r, c]) * 10))]
            for c in range(rgb.shape[1])) + "|")
