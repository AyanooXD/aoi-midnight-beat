"""Numeric proportion audit - far more reliable than eyeballing an ASCII render."""
import bpy
import math
from mathutils import Vector

BANDS = [(0.00, 0.10), (0.10, 0.30), (0.30, 0.50), (0.50, 0.70), (0.70, 0.88),
         (0.88, 0.98), (0.98, 1.10), (1.10, 1.22), (1.22, 1.32), (1.32, 1.40),
         (1.40, 1.50), (1.50, 1.64)]


def audit(label=""):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    per_obj = {}
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        n = 0
        for v in me.vertices:
            p = mw @ v.co
            pts.append(p)
            n += 1
        ev.to_mesh_clear()
        per_obj[ob.name] = (n, ob.matrix_world @ Vector(
            (sum(v.co.x for v in ob.data.vertices) / max(1, len(ob.data.vertices)), 0, 0)))

    if not pts:
        print("NO MESH")
        return
    zmin = min(p.z for p in pts)
    zmax = max(p.z for p in pts)
    xmin = min(p.x for p in pts)
    xmax = max(p.x for p in pts)
    ymin = min(p.y for p in pts)
    ymax = max(p.y for p in pts)
    print("=== BOUNDS %s ===" % label)
    print(" height Z %.4f .. %.4f  (%.3f m)" % (zmin, zmax, zmax - zmin))
    print(" width  X %.4f .. %.4f  (%.3f m)" % (xmin, xmax, xmax - xmin))
    print(" depth  Y %.4f .. %.4f  (%.3f m)" % (ymin, ymax, ymax - ymin))
    print(" heads tall = %.2f" % ((zmax - zmin) / 0.25))

    print("\n=== SILHOUETTE WIDTH BY HEIGHT BAND (metres) ===")
    for lo, hi in BANDS:
        sel = [p for p in pts if lo <= p.z < hi]
        if not sel:
            print("  z %.2f-%.2f : (empty)" % (lo, hi))
            continue
        a, b = min(p.x for p in sel), max(p.x for p in sel)
        # count distinct x clusters to detect merged limbs
        xs = sorted(set(round(p.x, 3) for p in sel))
        clusters = 1
        for i in range(1, len(xs)):
            if xs[i] - xs[i - 1] > 0.02:
                clusters += 1
        print("  z %.2f-%.2f : width %.3f  (x %+.3f..%+.3f)  x-clusters=%d"
              % (lo, hi, b - a, a, b, clusters))

    print("\n=== PER-OBJECT WORLD BOUNDS ===")
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        mw = ob.matrix_world
        cs = [mw @ v.co for v in ob.data.vertices]
        print("  %-18s x[%+.3f,%+.3f] y[%+.3f,%+.3f] z[%+.3f,%+.3f]"
              % (ob.name, min(c.x for c in cs), max(c.x for c in cs),
                 min(c.y for c in cs), max(c.y for c in cs),
                 min(c.z for c in cs), max(c.z for c in cs)))
