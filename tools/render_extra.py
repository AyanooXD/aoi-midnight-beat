"""Wireframe + texture contact sheet + verification of every preview."""
import bpy
import os
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio
import expose

OUT = "/tmp/aoi_previews"
BLEND = "/tmp/aoi_asset.blend"


def wireframe(path="wireframe.png", res=(760, 1060)):
    """Real wireframe: duplicate the asset as edges and render it as a mesh."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = bpy.data.libraries.load(BLEND)
    tmp = "/tmp/_wf.blend"
    bpy.ops.wm.save_as_mainfile(filepath=tmp)
    bpy.ops.wm.open_mainfile(filepath=BLEND)

    sc = bpy.context.scene
    cam = studio.build_studio(res=res, samples=1, floor=True)
    studio.place_cam(cam, yaw_deg=0, pitch_deg=0, dist=3.45,
                     target=(0, 0, 0.86), lens=85)

    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.view_settings.view_transform = 'Standard'
    sh = sc.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'SINGLE'
    sh.single_color = (0.10, 0.11, 0.14)
    sh.show_shadows = False
    sh.show_cavity = False
    sh.show_specular_highlight = False
    sh.show_object_outline = True
    sh.object_outline_color = (0.02, 0.02, 0.03)
    sh.show_xray = True
    sh.xray_alpha = 0.55

    # Build an explicit edge mesh so the wireframe is real geometry, not an overlay
    meshes = [o for o in sc.objects if o.type == 'MESH' and o.name.startswith("AOI_")]
    bm_edges = bpy.data.meshes.new("WF_EDGES")
    bm_edges.from_pydata([(0, 0, 0)] * 8, [], [])
    bm_edges.update()
    # Collect every unique mesh edge as a wire primitive
    for o in meshes:
        m = o.data
        verts, edges = [], []
        for e in m.edges:
            a = m.vertices[e.vertices[0]].co
            b = m.vertices[e.vertices[1]].co
            verts.append((a.x, a.y, a.z))
            verts.append((b.x, b.y, b.z))
            edges.append((len(verts) - 2, len(verts) - 1))
        me = bpy.data.meshes.new("WF_" + o.name)
        me.from_pydata(verts, edges, [])
        me.update()
        ob = bpy.data.objects.new("WF_" + o.name, me)
        sc.collection.objects.link(ob)
        o.hide_render = True
        mat = bpy.data.materials.new("WFM")
        mat.use_nodes = True
        mat.diffuse_color = (0.55, 0.62, 0.85, 1)
        nt = mat.node_tree
        for n in list(nt.nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nt.nodes.remove(n)
        out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs[0].default_value = (0.52, 0.58, 0.82, 1)
        em.inputs[1].default_value = 2.2
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        me.materials.append(mat)

    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 8
    sc.cycles.use_denoising = False
    sc.render.film_transparent = False
    sc.render.filepath = os.path.join(OUT, path)
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


def texture_sheet(path="textures.png", size=(1160, 1160)):
    names = [("aoi_skin_basecolor", "skin base"), ("aoi_skin_normal", "skin normal"),
             ("aoi_skin_roughness", "skin rough"), ("aoi_skin_ao", "skin AO"),
             ("aoi_hair_basecolor", "hair base"), ("aoi_hair_normal", "hair normal"),
             ("aoi_hair_roughness", "hair rough"),
             ("aoi_eye_basecolor", "eye base"), ("aoi_eye_roughness", "eye rough"),
             ("aoi_cloth_outer_basecolor", "jacket base"),
             ("aoi_cloth_outer_normal", "jacket normal"),
             ("aoi_cloth_trim_basecolor", "trim base"),
             ("aoi_cloth_inner_basecolor", "top/sock base"),
             ("aoi_denim_basecolor", "denim base"),
             ("aoi_shoe_basecolor", "shoe base"),
             ("aoi_metal_basecolor", "metal base")]
    cols, rows = 4, 4
    cw, ch = size[0] // cols, size[1] // rows
    sheet = Image.new("RGB", size, (16, 17, 21))
    dr = ImageDraw.Draw(sheet)
    n = 0
    for i, (fn, label) in enumerate(names):
        p = os.path.join("/tmp/aoi_tex", fn + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        src = os.path.getsize(p)
        im.thumbnail((cw - 10, ch - 30))
        cx, cy = (i % cols) * cw + 5, (i // cols) * ch + 22
        sheet.paste(im, (cx, cy))
        dr.text((cx, cy - 15), "%s  %dx%d" % (label, im.width, im.height),
                fill=(205, 210, 220))
        n += 1
    full = os.path.join(OUT, path)
    sheet.save(full)
    return full, n


def verify_all():
    print("\n" + "=" * 70)
    print("PREVIEW VERIFICATION (measured, not assumed)")
    print("=" * 70)
    rows = []
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".png"):
            continue
        p = os.path.join(OUT, f)
        im = Image.open(p).convert("RGB")
        a = np.asarray(im).astype(np.float32) / 255.0
        lum = a @ np.array([0.299, 0.587, 0.114])
        sat = float(((a.max(2) - a.min(2)) / np.maximum(a.max(2), 1e-6)).mean())
        s = expose.subject_stats(p)
        rows.append((f, im.width, im.height, os.path.getsize(p),
                     100 * s.get("subject_frac", 0), s.get("mean_lum", 0),
                     s.get("p5", 0), sat))
        print("  %-18s %4dx%-4d %7d B  subject %5.1f%%  meanL %.3f  p5 %.3f  sat %.3f"
              % (f, im.width, im.height, os.path.getsize(p),
                 rows[-1][4], rows[-1][5], rows[-1][6], rows[-1][7]))
    print("\n  %d preview images" % len(rows))
    return rows


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("wire", "all"):
        print("wireframe ->", wireframe())
    if mode in ("tex", "all"):
        p, n = texture_sheet()
        print("texture sheet ->", p, "(%d tiles)" % n)
    verify_all()