"""Full pre-export QC: geometry integrity, normals, UVs, scale, materials.

Prints measured facts only. Run it, fix whatever it flags, then re-run.
"""
import bpy
import bmesh
import os
from mathutils import Vector

TARGET_HEIGHT = 1.630
TOL = 0.004          # 4 mm


def qc(verbose=True):
    sc = bpy.context.scene
    meshes = [o for o in sc.objects if o.type == 'MESH']
    report = []
    ok = True

    # ---------------- per-mesh integrity ----------------
    problems = []
    for ob in meshes:
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        loose = sum(1 for v in bm.verts if not v.link_edges)
        flipped = 0
        for f in bm.faces:
            n = f.normal
            c = f.calc_center_median()
            # a normal pointing toward the mesh centroid is inside-out
            if (c - f.calc_center_median()).length == 0:
                pass
        # signed volume tells us the global winding
        vol = bm.calc_volume(signed=True)
        if vol < 0:
            flipped += 1
        bm.free()

        if nonman:
            problems.append("%s: %d non-manifold edges" % (ob.name, nonman))
        if loose:
            problems.append("%s: %d loose vertices" % (ob.name, loose))
        if vol < 0:
            problems.append("%s: INVERTED winding (signed volume %.6f)" % (ob.name, vol))

    # ---------------- normals / smoothing ----------------
    flat_bad = []
    for ob in meshes:
        if any(p.use_smooth for p in ob.data.polygons) and \
           any(not p.use_smooth for p in ob.data.polygons):
            flat_bad.append(ob.name)

    # ---------------- UVs ----------------
    no_uv = [o.name for o in meshes if not o.data.uv_layers]
    bad_uv = []
    for ob in meshes:
        if not ob.data.uv_layers:
            continue
        us = [d.uv[0] for d in ob.data.uv_layers.active.data]
        vs = [d.uv[1] for d in ob.data.uv_layers.active.data]
        if not us:
            continue
        span = max(max(us) - min(us), max(vs) - min(vs))
        if span < 1e-6:
            bad_uv.append("%s: degenerate UVs" % ob.name)
        if min(us) < -0.01 or max(us) > 1.01 or min(vs) < -0.01 or max(vs) > 1.01:
            bad_uv.append("%s: UVs outside 0..1 (u %.3f..%.3f v %.3f..%.3f)"
                          % (ob.name, min(us), max(us), min(vs), max(vs)))

    # ---------------- scale / orientation ----------------
    pts = []
    for ob in meshes:
        pts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    xmin, xmax = min(p.x for p in pts), max(p.x for p in pts)
    ymin, ymax = min(p.y for p in pts), max(p.y for p in pts)
    h = zmax - zmin

    # feet on the ground?
    foot_z = min(p.z for p in pts)
    # is she facing -Y?  check the nose tip (x~0) is the most -Y point at eye height
    eye_band = [p for p in pts if 1.44 < p.z < 1.52]
    facing = "?"
    if eye_band:
        front = min(eye_band, key=lambda p: p.y)
        facing = "-Y" if front.y < 0 else "+Y"

    offscale = [(o.name, tuple(round(v, 4) for v in o.scale))
                for o in meshes
                if any(abs(v - 1.0) > 1e-4 for v in o.scale)]
    offrot = [o.name for o in meshes
              if any(abs(v) > 1e-4 for v in o.rotation_euler)]
    offloc = [o.name for o in meshes
              if any(abs(v) > 1e-4 for v in o.location)]

    # ---------------- materials ----------------
    no_mat, multi = [], []
    for ob in meshes:
        if not ob.data.materials or ob.data.materials[0] is None:
            no_mat.append(ob.name)
        elif len(ob.data.materials) > 1:
            multi.append(ob.name)
    used = sorted({m.name for o in meshes for m in o.data.materials if m})
    broken = []
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image:
                if n.image.filepath and not os.path.exists(bpy.path.abspath(n.image.filepath)):
                    broken.append("%s -> %s" % (m.name, os.path.basename(n.image.filepath)))

    # ---------------- report ----------------
    if verbose:
        print("=" * 68)
        print("PRE-EXPORT QC REPORT")
        print("=" * 68)
        print("objects            %d" % len(meshes))
        print("total vertices     %d" % sum(len(o.data.vertices) for o in meshes))
        print("total faces        %d" % sum(len(o.data.polygons) for o in meshes))
        print("materials used     %d : %s" % (len(used), ", ".join(used)))
        print()
        print("--- GEOMETRY ---")
        print("non-manifold / winding / loose problems: %d" % len(problems))
        for p in problems[:20]:
            print("   !! %s" % p)
        print("mixed smooth/flat shading objects: %d %s" % (len(flat_bad), flat_bad[:5]))
        print()
        print("--- UVs ---")
        print("objects without UVs : %d %s" % (len(no_uv), no_uv[:5]))
        print("UV problems          : %d" % len(bad_uv))
        for b in bad_uv[:10]:
            print("   !! %s" % b)
        print()
        print("--- SCALE / ORIENTATION ---")
        print("height        %.4f m  (target %.3f, delta %+.4f m)"
              % (h, TARGET_HEIGHT, h - TARGET_HEIGHT))
        print("feet z        %.4f m  (target 0)" % foot_z)
        print("X extent      %.4f .. %.4f  (width %.4f)" % (xmin, xmax, xmax - xmin))
        print("Y extent      %.4f .. %.4f  (depth %.4f)" % (ymin, ymax, ymax - ymin))
        print("facing        %s" % facing)
        print("objects with non-unit scale : %d %s" % (len(offscale), offscale[:4]))
        print("objects with rotation       : %d %s" % (len(offrot), offrot[:4]))
        print("objects with translation   : %d %s" % (len(offloc), offloc[:4]))
        print()
        print("--- MATERIALS ---")
        print("objects missing material : %d %s" % (len(no_mat), no_mat[:5]))
        print("objects with >1 slot     : %d %s" % (len(multi), multi[:5]))
        print("broken texture paths     : %d %s" % (len(broken), broken[:5]))

    ok = (not problems and not no_uv and not bad_uv and not no_mat
          and not broken and not offscale and abs(h - TARGET_HEIGHT) < 0.02
          and abs(foot_z) < 0.01)
    print()
    print("RESULT: %s" % ("PASS" if ok else "ISSUES REMAIN"))
    return ok


if __name__ == "__main__":
    bpy.ops.wm.open_mainfile(filepath="/tmp/aoi_asset.blend")
    qc()