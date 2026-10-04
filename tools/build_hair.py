"""Part 3 - hair.

Built as separate, efficiently-tessellated objects:
  AOI_Hair_Scalp   - cap over the skull
  AOI_Hair_Back    - long back mass
  AOI_Hair_Bangs   - parted fringe (several tapered strands, joined)
  AOI_Hair_Side_R  - cheek-length side lock (+mirrored L)
  AOI_Hair_Tail_R  - twin tail (+mirrored L)
"""
import bpy
import math
from mathutils import Vector
from aoi_lib import (new_mesh_obj, weld, subdivide, mirror_dup, catmull_rom,
                     loft, loft_spine, grid_surface, solidify, activate_all)
from build_body import head_surface, head_t_from_z, R

SCALP_T = 0.0125         # distance the hair sits off the skull
ROOT_Z = 1.5580          # hairline: above the brows (1.542) and the eye top (1.515),
                         # so hair never covers the eyes
FRINGE_TIP_Z = 1.5290    # where the fringe hangs to

# head_surface: x = RX*sin(a), y = RY*cos(a)  ->  a=pi is the FRONT (-Y),
# a=+pi/2 is the RIGHT side (+X).
FRONT_A = math.pi


def _a_for_x(x):
    """Angle on the front of the head whose surface x matches `x`."""
    t = head_t_from_z(FRINGE_TIP_Z)
    sinphi = math.sin(math.pi * t)
    s = max(0.15, min(0.98, x / (0.084 * sinphi)))
    return FRONT_A - math.asin(s)


def _shell(name, t0, t1, nu=30, nv=12, scale=1.0, thick=0.0):
    """A patch of hair that follows the skull from t0 -> t1, offset outward."""
    rows = []
    for j in range(nv):
        t = t0 + (t1 - t0) * j / (nv - 1)
        row = []
        for i in range(nu):
            a = 2 * math.pi * i / nu
            p = head_surface(a, t)
            n = _outward(a, t)
            row.append(p + n * (SCALP_T * scale))
        rows.append(row)
    return _sheet(name, rows, thick)


def _outward(a, t):
    """Approximate outward normal of the head surface."""
    e = 0.004
    da = head_surface(a + e, t) - head_surface(a - e, t)
    dt = head_surface(a, min(1.0, t + e)) - head_surface(a, max(0.0, t - e))
    n = dt.cross(da)
    if n.length < 1e-9:
        return Vector((0, 0, 1))
    n.normalize()
    c = head_surface(a, t) - Vector((0, 0.010, 1.505))
    if n.dot(c) < 0:
        n = -n
    return n


def _sheet(name, rows, thick=0.0):
    verts, faces = [], []
    for r in rows:
        verts.extend(r)
    C = len(rows[0])
    for i in range(len(rows) - 1):
        for j in range(C - 1):
            a = i * C + j
            faces.append((a, a + 1, a + C + 1, a + C))
    ob = new_mesh_obj(name, verts, faces)
    if thick:
        solidify(ob, thick)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


# --------------------------------------------------------------------------- #
def build_scalp():
    """Hair shell over the skull, from the hairline up over the crown."""
    t_hair = head_t_from_z(ROOT_Z)
    rows = []
    NV, NU = 16, 34
    for j in range(NV):
        t = t_hair + (0.995 - t_hair) * j / (NV - 1)
        row = []
        for i in range(NU):
            a = 2 * math.pi * i / NU
            p = head_surface(a, t)
            n = _outward(a, t)
            row.append(p + n * SCALP_T)
        rows.append(row)
    return _sheet("AOI_Hair_Scalp", rows, 0.0035)


def build_back():
    """Long tapered mass down the back, widening then tapering to a point."""
    rows = []
    NV, NU = 20, 18
    t_top = head_t_from_z(1.585)
    for j in range(NV):
        t = j / (NV - 1)
        z = 1.585 - t * 0.560                     # down to ~1.025 (mid-back)
        tt = head_t_from_z(z)
        w = 0.098 * (1.0 - 0.30 * t) * (1 - t ** 3 * 0.92)
        d = 0.062 * (1.0 - 0.20 * t) * (1 - t ** 2.4 * 0.85)
        row = []
        for i in range(NU):
            a = 2 * math.pi * i / NU
            # flatten the back mass against the head/shoulders
            cx, cz = Vector((0, 0.012, 1.505)), z
            if cz > 1.560:
                p = head_surface(a, head_t_from_z(cz)) + _outward(a, head_t_from_z(cz)) * 0.013
            else:
                ang = a
                x = w * math.sin(ang)
                y = 0.012 + d * math.cos(ang) * 1.02
                if y < 0:                       # keep it behind the neck
                    y *= 0.55
                y += 0.018 * (z - 1.4)
                p = Vector((x, y, cz))
            row.append(p)
        rows.append(row)
    return _sheet("AOI_Hair_Back", rows, 0.0040)


def _strand(name, spine, w0, w1, n=9, thick=0.0035, flat=1.0):
    """A tapered, slightly flattened strand lofted along a spine."""
    rings = []
    P = [Vector(p) for p in spine]
    for i in range(len(P)):
        t = i / (len(P) - 1)
        if i == 0:
            d = P[1] - P[0]
        elif i == len(P) - 1:
            d = P[-1] - P[-2]
        else:
            d = P[i + 1] - P[i - 1]
        d.normalize()
        up = Vector((0, 1, 0))
        if abs(d.dot(up)) > 0.95:
            up = Vector((1, 0, 0))
        s = d.cross(up).normalized()
        u = s.cross(d).normalized()
        w = (w0 * (1 - t) + w1 * t) * (0.55 + 0.45 * math.sin(math.pi * (0.15 + 0.85 * t)))
        ring = []
        for k in range(n):
            ang = 2 * math.pi * k / n
            p = P[i] + s * (math.cos(ang) * w) + u * (math.sin(ang) * w * flat)
            ring.append(p)
        rings.append(ring)
    ob = loft(name, rings)
    weld(ob)
    solidify(ob, thick)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def build_bangs():
    """Parted straight fringe: tapered strands swept from the hairline down."""
    strands = []
    # (root x on the head, tip x drift, root z, tip z, y push off the face)
    defs = [
        (-0.076, -0.028, 1.590, 1.5455, 0.020),
        (-0.048, -0.018, 1.598, 1.5330, 0.018),
        (-0.018, -0.006, 1.604, 1.5290, 0.016),
        (0.014, 0.005, 1.604, 1.5290, 0.016),
        (0.046, 0.018, 1.598, 1.5340, 0.018),
        (0.074, 0.029, 1.590, 1.5470, 0.020),
    ]
    for i, (rx, tdx, rz, tz, push) in enumerate(defs):
        a = _a_for_x(rx)
        tt = head_t_from_z(rz)
        root = head_surface(a, tt) + _outward(a, tt) * (SCALP_T + 0.0015)
        tipx = rx + tdx
        a_t = _a_for_x(tipx)
        tip = head_surface(a_t, head_t_from_z(tz)) + Vector((0, -push, 0))
        spine = [root,
                 root.lerp(tip, 0.34) + Vector((0, -push * 0.35, 0.004)),
                 root.lerp(tip, 0.72) + Vector((0, -push * 0.25, 0.003)),
                 tip]
        strands.append(_strand("AOI_Bang_%d" % i, spine, 0.0175, 0.0050,
                               n=10, thick=0.0030, flat=0.55))
    activate_all(strands)
    bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = "AOI_Hair_Bangs"
    ob.data.name = ob.name
    weld(ob)
    return ob


def build_side_lock():
    """Cheek-length side lock in front of the ear, tapering to a point."""
    rz = 1.572
    a0 = math.pi / 2 - R(26)          # just in front of the right ear
    tt = head_t_from_z(rz)
    root = head_surface(a0, tt) + _outward(a0, tt) * (SCALP_T + 0.002)
    spine = [root,
             root + Vector((0.002, -0.004, -0.058)),
             Vector((root.x + 0.004, root.y - 0.018, root.z - 0.125)),
             Vector((root.x + 0.002, root.y - 0.030, root.z - 0.188)),
             Vector((root.x - 0.002, root.y - 0.036, root.z - 0.232))]
    return _strand("AOI_Hair_Side_R", spine, 0.0250, 0.0055, n=11, thick=0.0035, flat=0.62)


def build_tail():
    """High twin tail: a long, slightly curved tapered mass."""
    root = Vector((0.082, 0.040, 1.578))
    spine = [root,
             root + Vector((0.048, 0.018, 0.028)),
             root + Vector((0.086, 0.034, -0.034)),
             root + Vector((0.102, 0.038, -0.134)),
             root + Vector((0.098, 0.028, -0.252)),
             root + Vector((0.084, 0.010, -0.362)),
             root + Vector((0.066, -0.012, -0.442))]
    ob = _strand("AOI_Hair_Tail_R", spine, 0.0350, 0.0090, n=13, thick=0.0040, flat=0.85)
    mirror_dup(ob, "AOI_Hair_Tail_L")
    return ob


def build_all():
    out = [build_scalp(), build_back()]
    bangs = build_bangs()
    mirror_dup(bangs, "AOI_Hair_Bangs_L")
    out.append(bangs)
    sl = build_side_lock()
    mirror_dup(sl, "AOI_Hair_Side_L")
    out += [sl, build_tail()]
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import build_body
    build_body.build_all()
    for ob in build_all():
        print(" %-20s v=%5d f=%5d" % (ob.name, len(ob.data.vertices), len(ob.data.polygons)))
