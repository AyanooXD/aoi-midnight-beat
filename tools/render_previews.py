"""Render the marketplace preview set and verify each image by measurement."""
import bpy
import os
import sys
import math
import shutil
import numpy as np
from PIL import Image
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio
import expose

OUT = "/tmp/aoi_previews"
BLEND = "/tmp/aoi_asset.blend"
NAME = "AOI_MIDNIGHT_BEAT"


def reset_scene():
    for o in list(bpy.data.objects):
        if o.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(o, do_unlink=True)


def hero(cam):
    """Three-quarter hero shot, slightly above eye level."""
    studio.place_cam(cam, 34, 6, 3.30, target=(0, 0, 0.88), lens=80)


def views():
    return [
        ("front", dict(yaw_deg=0, pitch_deg=0, dist=3.45, target=(0, 0, 0.86), lens=85)),
        ("side", dict(yaw_deg=90, pitch_deg=0, dist=3.45, target=(0, 0, 0.86), lens=85)),
        ("back", dict(yaw_deg=180, pitch_deg=0, dist=3.45, target=(0, 0, 0.86), lens=85)),
        ("face", dict(yaw_deg=8, pitch_deg=2, dist=0.92, target=(0, 0, 1.500), lens=85)),
        ("details", dict(yaw_deg=46, pitch_deg=10, dist=0.80, target=(0.02, -0.02, 1.30), lens=70)),
    ]


def render_set(samples=90, res=(1000, 1400), face_res=(1200, 1400)):
    os.makedirs(OUT, exist_ok=True)
    cam = studio.build_studio(res=res, samples=samples)
    results = {}

    for name, v in views():
        r = face_res if name in ("face", "details") else res
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = r
        studio.place_cam(cam, **v)
        p = os.path.join(OUT, "%s.png" % name)
        studio.render(p, samples=samples)
        results[name] = p

    # hero
    bpy.context.scene.render.resolution_x = 1400
    bpy.context.scene.render.resolution_y = 1400
    hero(cam)
    p = os.path.join(OUT, "hero.png")
    studio.render(p, samples=samples + 30)
    results["hero"] = p
    return results, cam


def render_wireframe(cam, path):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.view_settings.view_transform = 'Standard'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'SINGLE'
    sh.single_color = (0.72, 0.74, 0.80)
    sh.show_shadows = False
    sh.show_specular_highlight = False
    sh.show_cavity = False
    sh.show_object_outline = True
    sh.object_outline_color = (0.05, 0.06, 0.09)
    # wireframe is a viewport overlay; enable it and render the viewport
    sh.show_xray = True
    sc.display.render_aa = '8'
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1400
    sc.render.film_transparent = False
    studio.place_cam(cam, 0, 0, 3.45, target=(0, 0, 0.86), lens=85)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_textures(path, size=(1100, 1100)):
    """Contact sheet of the actual texture maps that ship with the asset."""
    import textures as tex
    names = ["aoi_skin_basecolor", "aoi_skin_normal", "aoi_skin_roughness",
             "aoi_hair_basecolor", "aoi_hair_normal", "aoi_hair_roughness",
             "aoi_eye_basecolor", "aoi_eye_roughness",
             "aoi_cloth_outer_basecolor", "aoi_cloth_outer_normal",
             "aoi_cloth_trim_basecolor", "aoi_denim_basecolor",
             "aoi_cloth_inner_basecolor", "aoi_shoe_basecolor",
             "aoi_metal_basecolor", "aoi_metal_roughness"]
    cols, rows = 4, 4
    cell = size[0] // cols
    cellh = size[1] // rows
    sheet = Image.new("RGB", size, (18, 19, 24))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    placed = 0
    for i, n in enumerate(names):
        p = os.path.join(tex.OUT or "/tmp/aoi_tex", n + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell - 8, cellh - 26))
        cx = (i % cols) * cell + 4
        cy = (i // cols) * cellh + 20
        sheet.paste(im, (cx, cy))
        dr.text((cx + 2, cy - 16), n.replace("aoi_", ""), fill=(200, 205, 215))
        placed += 1
    sheet.save(path)
    return path, placed


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    import textures as tex
    tex.OUT = "/tmp/aoi_tex"
    results, cam = render_set()

    wf = render_wireframe(cam, os.path.join(OUT, "wireframe.png"))
    tp, n = render_textures(os.path.join(OUT, "textures.png"))
    results["wireframe"] = wf
    results["textures"] = tp
    print("\n=== PREVIEW VERIFICATION ===")
    for k, p in sorted(results.items()):
        s = expose.subject_stats(p)
        if not s.get("ok"):
            print("  %-10s FAILED: %s" % (k, s))
            continue
        im = Image.open(p).convert('RGB')
        a = np.asarray(im).astype(np.float32) / 255.0
        sat = float(((a.max(2) - a.min(2)) / np.maximum(a.max(2), 1e-6)).mean())
        print("  %-10s %5dx%-5d subject %5.1f%%  meanL %.3f  p5 %.3f  sat %.3f"
              % (k, im.width, im.height, 100 * s["subject_frac"], s["mean_lum"],
                 s["p5"], sat))
    print("  texture sheet tiles: %d" % n)
    return results


if __name__ == "__main__":
    main()