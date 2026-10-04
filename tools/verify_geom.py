"""Exact, render-independent verification of facial feature placement + symmetry."""
import bpy
from mathutils import Vector
from collections import defaultdict


def world_pts(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def centroid(ob):
    pts = world_pts(ob)
    return sum(pts, Vector()) / len(pts)


def bounds(ob):
    pts = world_pts(ob)
    return (min(p.x for p in pts), max(p.x for p in pts),
            min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts), max(p.z for p in pts))


def mirror_iou_geom(nameR, nameL, axis=0):
    """Overlap of a feature against its own mirror image, in world space."""
    R = bpy.context.scene.objects[nameR]
    L = bpy.context.scene.objects[nameL]
    pr = world_pts(R)
    pl = [Vector((-p.x if axis == 0 else p.x, p.y, p.z)) for p in world_pts(L)]
    # raster-free overlap test: fraction of R points inside L's mirrored bbox
    lo = [min(p[i] for p in pl) for i in range(3)]
    hi = [max(p[i] for p in pl) for i in range(3)]
    inside = sum(1 for p in pr if all(lo[i] - 1e-6 <= p[i] <= hi[i] + 1e-6 for i in range(3)))
    return inside / max(1, len(pr))


def report():
    objs = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}

    print("=== FEATURE CENTRES (world space) ===")
    for n in sorted(objs):
        if not any(k in n for k in ("Eye_", "Lash", "Brow", "Mouth", "Nose", "Ear_")):
            continue
        c = centroid(objs[n])
        b = bounds(objs[n])
        print("  %-18s c=(%+.4f,%+.4f,%+.4f)  z-span %.4f..%.4f"
              % (n, c.x, c.y, c.z, b[4], b[5]))

    print("\n=== SYMMETRY (fraction of R feature inside mirrored-L bbox) ===")
    pairs = [("AOI_Eye_R", "AOI_Eye_L"), ("AOI_Lash_R", "AOI_Lash_L"),
             ("AOI_LashLow_R", "AOI_LashLow_L"), ("AOI_Brow_R", "AOI_Brow_L"),
             ("AOI_EyeSocket_R", "AOI_EyeSocket_L"), ("AOI_Ear_R", "AOI_Ear_L"),
             ("AOI_Arm_R", "AOI_Arm_L"), ("AOI_Hand_R", "AOI_Hand_L"),
             ("AOI_Leg_R", "AOI_Leg_L"), ("AOI_Foot_R", "AOI_Foot_L")]
    worst = 1.0
    for r, l in pairs:
        if r not in objs or l not in objs:
            continue
        v = mirror_iou_geom(r, l)
        worst = min(worst, v)
        flag = "OK " if v > 0.985 else "** MISMATCH **"
        print("  %-18s vs %-18s %.4f  %s" % (r, l, v, flag))
    print("  worst = %.4f" % worst)

    print("\n=== PROPORTION CHECKS ===")
    hb = bounds(objs["AOI_Head"])
    chin, crown = hb[4], hb[5]
    H = crown - chin
    for n, label in (("AOI_Eye_R", "eye"), ("AOI_Brow_R", "brow"),
                     ("AOI_Nose", "nose tip"), ("AOI_Mouth", "mouth"),
                     ("AOI_Ear_R", "ear centre")):
        if n not in objs:
            continue
        c = centroid(objs[n])
        print("  %-14s at %.1f%% of head height" % (label, 100 * (c.z - chin) / H))
    ey = centroid(objs["AOI_Eye_R"])
    print("  eye spacing (centre to centre) = %.4f m  (%.2f eye widths)"
          % (2 * abs(ey.x), 2 * abs(ey.x) / 0.0470))
    eb = bounds(objs["AOI_Eye_R"])
    print("  eye box = %.4f x %.4f m" % (eb[1] - eb[0], eb[5] - eb[4]))
    # do the eye parts actually sit in FRONT of the skull at that spot?
    ys = [p.y for p in world_pts(objs["AOI_EyeSocket_R"])]
    print("  socket y-range %.4f..%.4f ; eyeball sits proud by %.4f m"
          % (min(ys), max(ys), min(p.y for p in world_pts(objs["AOI_Eye_R"]))
             - min(ys)))
    return worst


if __name__ == "__main__":
    report()
