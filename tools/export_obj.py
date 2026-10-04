"""Export the marketplace package: MODEL/*.obj + *.mtl, TEXTURES/, PREVIEWS/.

Then re-import the OBJ into a clean scene and verify geometry, UVs, materials
and textures survived the round trip. Export is not "done" until that passes.
"""
import bpy
import os
import re
import shutil
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BLEND = "/tmp/aoi_asset.blend"
ROOT = "/tmp/AOI_MIDNIGHT_BEAT"
NAME = "AOI_MIDNIGHT_BEAT"
OBJ = "aoi_character"


def clean():
    if os.path.isdir(ROOT):
        shutil.rmtree(ROOT)
    for d in ("MODEL", "TEXTURES", "PREVIEWS"):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)


# --------------------------------------------------------------------------- #
#  export
# --------------------------------------------------------------------------- #
def export_obj():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene

    # Only ship the character: no lights, no cameras, no studio floor.
    for o in list(sc.objects):
        if o.type in ('LIGHT', 'CAMERA') or not o.name.startswith("AOI_"):
            bpy.data.objects.remove(o, do_unlink=True)

    # Blender's OBJ writer emits relative map_Kd paths; make sure they are.
    out_dir = os.path.join(ROOT, "MODEL")
    tex_dir = os.path.join(ROOT, "TEXTURES")
    for img in bpy.data.images:
        if img.source == 'FILE' and img.filepath:
            base = os.path.basename(bpy.path.abspath(img.filepath))
            dest = os.path.join(tex_dir, base)
            if not os.path.exists(dest):
                shutil.copy2(bpy.path.abspath(img.filepath), dest)
            img.filepath_raw = dest

    bpy.ops.wm.obj_export(
        filepath=os.path.join(out_dir, OBJ + ".obj"),
        export_selected_objects=False,
        apply_modifiers=True,
        export_materials=True,
        export_uv=True,
        export_normals=True,
        export_triangulated_mesh=False,
        path_mode='COPY',
        forward_axis='NEGATIVE_Z',
        up_axis='Y',
    )
    obj = os.path.join(out_dir, OBJ + ".obj")
    mtl = os.path.join(out_dir, OBJ + ".mtl")
    relocate_textures(mtl)
    print("exported OBJ : %s (%d bytes)" % (obj, os.path.getsize(obj)))
    print("exported MTL : %s (%d bytes)" % (mtl, os.path.getsize(mtl)))
    return obj, mtl


def relocate_textures(mtl_path):
    """Textures must live in /TEXTURES/, not /MODEL/.

    Blender's OBJ writer copies images next to the OBJ and references them by
    bare filename. Move them into TEXTURES/ and rewrite every map_* reference
    to '../TEXTURES/<file>' so the shipped layout matches the spec and still
    resolves from any importer.
    """
    out_dir = os.path.join(ROOT, "MODEL")
    tex_dir = os.path.join(ROOT, "TEXTURES")
    os.makedirs(tex_dir, exist_ok=True)

    moved = 0
    for p in glob.glob(os.path.join(out_dir, "*.png")):
        dest = os.path.join(tex_dir, os.path.basename(p))
        shutil.move(p, dest)
        moved += 1

    with open(mtl_path) as fh:
        lines = fh.readlines()
    n = 0
    with open(mtl_path, "w") as fh:
        for l in lines:
            s = l.strip()
            if s.startswith("map_") and len(s.split()) >= 2:
                key, val = s.split(None, 1)
                val = val.strip()
                if val and not val.startswith("/") and not val.startswith(".."):
                    if os.path.exists(os.path.join(tex_dir, os.path.basename(val))):
                        fh.write("%s ../TEXTURES/%s\n" % (key, os.path.basename(val)))
                        n += 1
                        continue
            fh.write(l)
    print("textures moved to TEXTURES/: %d ; map refs rewritten: %d" % (moved, n))


def copy_previews():
    src = "/tmp/aoi_previews"
    names = {"hero": "hero.png", "front": "front.png", "side": "side.png",
             "back": "back.png", "face": "face.png", "details": "details.png",
             "wireframe": "wireframe.png", "textures": "textures.png"}
    n = 0
    for k, fn in names.items():
        p = os.path.join(src, fn)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(ROOT, "PREVIEWS", fn))
            n += 1
    return n


def count_obj():
    """Parse the OBJ itself and report what a buyer will actually load."""
    obj = os.path.join(ROOT, "MODEL", OBJ + ".obj")
    v = vt = vn = f = g = 0
    mats = set()
    objs = set()
    cur = None
    with open(obj) as fh:
        for line in fh:
            if line.startswith("v "):
                v += 1
            elif line.startswith("vt "):
                vt += 1
            elif line.startswith("vn "):
                vn += 1
            elif line.startswith("f "):
                f += 1
            elif line.startswith("g ") or line.startswith("o "):
                cur = line.split(None, 1)[1].strip()
                objs.add(cur)
            elif line.startswith("usemtl "):
                mats.add(line.split(None, 1)[1].strip())
    return dict(v=v, vt=vt, vn=vn, f=f, objects=len(objs), materials=len(mats))


# --------------------------------------------------------------------------- #
#  re-import verification
# --------------------------------------------------------------------------- #
def verify_reimport():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = os.path.join(ROOT, "MODEL", OBJ + ".obj")
    bpy.ops.wm.obj_import(filepath=obj, forward_axis='NEGATIVE_Z', up_axis='Y')

    # Which materials are *meant* to be textured? Read that from the MTL itself
    # rather than guessing, so the check reflects what actually shipped.
    textured = set()
    mtl_path = os.path.join(ROOT, "MODEL", OBJ + ".mtl")
    cur = None
    with open(mtl_path) as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("newmtl"):
                cur = s.split(None, 1)[1]
            elif s.startswith("map_Kd") and cur:
                textured.add(cur)

    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    pts = []
    no_mat, no_uv, no_tex, bad_tex = [], [], [], []
    mats = set()
    for o in meshes:
        pts += [o.matrix_world @ v.co for v in o.data.vertices]
        if not o.data.uv_layers:
            no_uv.append(o.name)
        ms = [m for m in o.data.materials if m]
        if not ms:
            no_mat.append(o.name)
        for m in ms:
            mats.add(m.name)
            ntex = 0
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == 'TEX_IMAGE':
                        fp = bpy.path.abspath(n.image.filepath)
                        if not os.path.exists(fp):
                            bad_tex.append("%s -> %s" % (m.name, n.image.name))
                        else:
                            ntex += 1
            # A material that ships a map_Kd MUST resolve at least one texture
            if m.name in textured and ntex == 0:
                no_tex.append("%s declares map_Kd but resolves no texture" % m.name)

    zmin = min(p.z for p in pts)
    zmax = max(p.z for p in pts)
    xmin = min(p.x for p in pts)
    xmax = max(p.x for p in pts)

    tri = 0
    for o in meshes:
        o.data.calc_loop_triangles()
        tri += len(o.data.loop_triangles)

    print("\n" + "=" * 66)
    print("RE-IMPORT VERIFICATION (fresh scene, OBJ loaded from disk)")
    print("=" * 66)
    print("objects re-imported   %d" % len(meshes))
    print("vertices              %d" % sum(len(o.data.vertices) for o in meshes))
    print("faces                 %d" % sum(len(o.data.polygons) for o in meshes))
    print("triangles             %d" % tri)
    print("materials             %d" % len(mats))
    print("  textured            %d : %s" % (len(textured), ", ".join(sorted(textured))))
    flat = sorted(mats - textured)
    print("  flat colour only    %d : %s" % (len(flat), ", ".join(flat)))
    print("objects missing UVs   %d %s" % (len(no_uv), no_uv[:4]))
    print("objects missing mat   %d %s" % (len(no_mat), no_mat[:4]))
    print("declared-but-unlinked textures : %d %s" % (len(no_tex), no_tex[:4]))
    print("broken texture files  %d %s" % (len(bad_tex), bad_tex[:4]))
    print("height %.4f m   width %.4f m   feet z %.4f" % (zmax - zmin, xmax - xmin, zmin))

    # every shipped texture must live in TEXTURES/
    tex_dir = os.path.join(ROOT, "TEXTURES")
    ntex_files = len([f for f in os.listdir(tex_dir) if f.endswith(".png")])
    strays = [f for f in os.listdir(os.path.join(ROOT, "MODEL")) if f.endswith(".png")]
    print("textures in TEXTURES/: %d ; stray png in MODEL/: %d" % (ntex_files, len(strays)))

    ok = (len(meshes) > 0 and not no_uv and not no_mat and not no_tex
          and not bad_tex and not strays
          and abs((zmax - zmin) - 1.6384) < 0.02 and abs(zmin - 0.0058) < 0.02)
    print()
    print("ROUND-TRIP: %s" % ("PASS" if ok else "FAIL"))
    return ok


if __name__ == "__main__":
    clean()
    export_obj()
    n = copy_previews()
    print("previews copied: %d" % n)
    c = count_obj()
    print("\n=== OBJ FILE CONTENTS (what the buyer loads) ===")
    for k, v in c.items():
        print("   %-10s %d" % (k, v))
    verify_reimport()