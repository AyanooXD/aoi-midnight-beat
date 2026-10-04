"""Part 4 - clothing and accessories.

Every garment is an offset shell around the body so cloth hugs the form
without intersecting it. The outfit is fully closed / general-audience:
cropped bomber jacket, inner top, pleated A-line skirt, socks, sneakers,
over-ear headphones, twin-tail ribbons, choker.
"""
import bpy
import math
from mathutils import Vector
from aoi_lib import (new_mesh_obj, weld, solidify, subdivide, mirror_dup,
                     loft_spine, section, catmull_rom, activate_all)
from build_body import (ACROMION_X, SHOULDER_Z, ARM_TILT, ARM_LEN, wrist_point,
                        arm_transform, R)

GAP = 0.0075            # cloth stand-off from the body


# --------------------------------------------------------------------------- #
#  torso shells: same profile as the body, pushed out by GAP
# --------------------------------------------------------------------------- #
TORSO_PROFILE = [
    (1.4050, 0.0455, 0.0460, 0.0045),
    (1.3500, 0.0620, 0.0545, 0.0040),
    (1.2950, 0.0800, 0.0605, 0.0030),
    (1.2400, 0.0945, 0.0655, 0.0010),
    (1.1900, 0.0965, 0.0670, 0.0000),
    (1.1400, 0.0870, 0.0630, -0.0010),
    (1.0800, 0.0760, 0.0585, -0.0020),
    (1.0300, 0.0755, 0.0590, -0.0020),
    (0.9850, 0.0830, 0.0640, -0.0010),
    (0.9400, 0.0900, 0.0670, 0.0000),
    (0.8950, 0.0885, 0.0665, 0.0010),
    (0.8600, 0.0800, 0.0620, 0.0020),
]


def _prof(lo, hi, gap, extra=0.0, samples=None):
    """Sample the body profile between two heights and inflate it by `gap`."""
    pts = [p for p in TORSO_PROFILE if lo - 1e-6 <= p[0] <= hi + 1e-6]
    if len(pts) < 2:
        pts = [p for p in TORSO_PROFILE]
    out = []
    n = samples or len(pts)
    for i in range(n):
        z = lo + (hi - lo) * i / (n - 1)
        # linear interp of the profile at this z
        lo_pt = max([p for p in TORSO_PROFILE if p[0] <= z], key=lambda p: p[0], default=TORSO_PROFILE[0])
        hi_pt = min([p for p in TORSO_PROFILE if p[0] >= z], key=lambda p: p[0], default=TORSO_PROFILE[-1])
        f = 0.0 if lo_pt[0] == hi_pt[0] else (z - lo_pt[0]) / (hi_pt[0] - lo_pt[0])
        w = lo_pt[1] + (hi_pt[1] - lo_pt[1]) * f
        d = lo_pt[2] + (hi_pt[2] - lo_pt[2]) * f
        yo = lo_pt[3] + (hi_pt[3] - lo_pt[3]) * f
        out.append((z, w + gap + extra, d + gap + extra, yo))
    return out


def _shell(name, keys, ring_n=28, p=0.92, cap=True):
    ob = loft_spine(name, keys, per_seg=4, ring_n=ring_n, p=p)
    weld(ob)
    return ob


def build_top():
    """Off-white fitted inner top, from the bust down to the waist."""
    keys = _prof(1.2320, 1.0400, GAP, samples=9)
    ob = _shell("AOI_Top", keys)
    return ob


def build_jacket():
    """Cropped bomber: an open-front shell + collar + hem + cuffs.

    Built as a full shell around the torso, then the front-centre verts are
    deleted so it reads as an OPEN jacket rather than a closed tube.
    """
    keys = _prof(1.3400, 1.0800, GAP + 0.006, samples=11)
    full = _shell("AOI_Jacket", keys, ring_n=32, p=0.95)

    # open the front: delete verts on the centre line that face -Y
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(full.data)
    kv = [v for v in bm.verts if abs(v.co.x) < 0.030 and v.co.y < -0.040]
    bmesh.ops.delete(bm, geom=kv, context='VERTS')
    bm.to_mesh(full.data)
    bm.free()
    full.data.update()

    for p in full.data.polygons:
        p.use_smooth = True
    solidify(full, 0.0035)
    return full


def build_jacket_trim():
    """Ribbed collar + hem + cuffs in the periwinkle accent colour."""
    out = []
    # collar: a ring around the neck
    keys = _prof(1.3450, 1.2850, GAP + 0.016, samples=5)
    collar = loft_spine("AOI_Jacket_Collar", keys, per_seg=3, ring_n=28, p=0.95)
    weld(collar)
    out.append(collar)

    # hem: a ring at the bottom of the jacket
    keys = _prof(1.1000, 1.0680, GAP + 0.014, samples=4)
    hem = loft_spine("AOI_Jacket_Hem", keys, per_seg=3, ring_n=28, p=0.95)
    weld(hem)
    out.append(hem)
    return out


def build_skirt():
    """Pleated A-line skirt with a flared hem."""
    # Pleats: modulate the radius with a cosine around the circumference.
    NU, NV = 48, 14
    PLEATS = 12
    rows = []
    for j in range(NV):
        t = j / (NV - 1)
        z = 0.9900 - t * 0.1450                 # waist -> hem
        w = 0.0790 + t * 0.0330                 # A-line flare
        d = 0.0650 + t * 0.0270
        row = []
        for i in range(NU):
            a = 2 * math.pi * i / NU
            pleat = 1.0 + 0.055 * math.cos(PLEATS * a) * (t ** 0.75)
            x = w * math.cos(a) * pleat
            y = d * math.sin(a) * pleat - 0.002
            row.append(Vector((x, y, z + 0.0025 * math.cos(PLEATS * a) * t)))
        rows.append(row)
    verts, faces = [], []
    for r in rows:
        verts.extend(r)
    C = NU
    for i in range(NV - 1):
        for j in range(C):
            a = i * C + j
            b = i * C + (j + 1) % C
            faces.append((a, b, b + C, a + C))
    ob = new_mesh_obj("AOI_Skirt", verts, faces)
    solidify(ob, 0.0030)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def build_socks():
    """Mid-calf socks following the leg."""
    leg = [(0.0800, 0.0268, 0.0276, -0.0020),
           (0.1800, 0.0292, 0.0310, -0.0015),
           (0.2800, 0.0355, 0.0385, -0.0010),
           (0.3800, 0.0428, 0.0468, -0.0010),
           (0.4600, 0.0452, 0.0500, -0.0010),
           (0.5400, 0.0436, 0.0472, -0.0008)]
    keys = [(z, w + 0.0035, d + 0.0035, yo) for z, w, d, yo in leg]
    ob = loft_spine("AOI_Sock_R", keys, per_seg=4, ring_n=20)
    weld(ob)
    ob.location = (0.0455, 0.0010, 0.0)          # same x/y offset as the leg
    mirror_dup(ob, "AOI_Sock_L")
    return ob


def build_shoe():
    """Sneaker: a closed shell over the foot + a chunky sole."""
    # upper: slightly larger than the foot, from the ankle to the toe
    up = [(0.0680, 0.0310, 0.0330, 0.0330),
          (0.0480, 0.0328, 0.0430, 0.0110),
          (0.0260, 0.0338, 0.0478, -0.0110),
          (0.0120, 0.0342, 0.0458, -0.0290),
          (0.0085, 0.0326, 0.0400, -0.0430),
          (0.0075, 0.0280, 0.0300, -0.0570),
          (0.0070, 0.0198, 0.0176, -0.0670),
          (0.0070, 0.0094, 0.0082, -0.0722)]
    upper = loft_spine("AOI_Shoe_R", [(z, w, d, y) for z, w, d, y in up],
                       per_seg=4, ring_n=18)
    weld(upper)
    upper.location = (0.0455, -0.0130, 0.0)

    # sole: a flat slab under the whole foot
    sole_keys = [(0.0090, 0.0330, 0.0330, 0.0350),
                 (0.0090, 0.0362, 0.0480, 0.0130),
                 (0.0085, 0.0368, 0.0530, -0.0110),
                 (0.0075, 0.0360, 0.0510, -0.0310),
                 (0.0068, 0.0330, 0.0440, -0.0470),
                 (0.0062, 0.0268, 0.0320, -0.0600),
                 (0.0058, 0.0150, 0.0180, -0.0690)]
    sole = loft_spine("AOI_Sole_R", sole_keys, per_seg=4, ring_n=18)
    weld(sole)
    sole.location = (0.0455, -0.0130, 0.0)
    for p in sole.data.polygons:
        p.use_smooth = True
    mirror_dup(upper, "AOI_Shoe_L")
    mirror_dup(sole, "AOI_Sole_L")
    return upper, sole


# --------------------------------------------------------------------------- #
#  accessories
# --------------------------------------------------------------------------- #
def build_headphones():
    """Over-ear headphones: padded band + two earcups."""
    out = []
    # band: an arc over the skull, just outside the hair
    NU, NV = 26, 8
    rows = []
    for j in range(NV):
        v = j / (NV - 1)
        rad = 0.1030 + v * 0.0100
        row = []
        for i in range(NU):
            a = math.pi * (i / (NU - 1))          # front-to-back over the top
            x = rad * math.cos(a)
            z = 1.4900 + 0.1300 * math.sin(a)
            # slightly wider than the skull so it clears the hair
            x *= 1.06
            row.append(Vector((x, 0.012, z)))
        rows.append(row)
    verts, faces = [], []
    for r in rows:
        verts.extend(r)
    C = NU
    for i in range(NV - 1):
        for j in range(C - 1):
            a = i * C + j
            faces.append((a, a + 1, a + C + 1, a + C))
    band = new_mesh_obj("AOI_Headband_R", verts, faces)
    solidify(band, 0.0060)
    for p in band.data.polygons:
        p.use_smooth = True
    mirror_dup(band, "AOI_Headband_L")
    out.append(band)

    # earcups: a rounded pad + a disc, sitting over the ears
    for sx, sfx in ((1, "R"), (-1, "L")):
        NU2, NV2 = 18, 10
        rows = []
        for j in range(NV2):
            vv = -1 + 2 * j / (NV2 - 1)
            row = []
            for i in range(NU2):
                uu = -1 + 2 * i / (NU2 - 1)
                # squashed ellipsoid facing outward in X
                rr = math.sqrt(max(0.0, 1 - uu * uu))
                x = sx * (0.1030 + 0.0180 * math.cos(math.pi * vv) * rr)
                y = 0.012 + 0.0320 * uu * rr
                z = 1.4870 + 0.0390 * vv * rr
                row.append(Vector((x, y, z)))
            rows.append(row)
        v2, f2 = [], []
        for r in rows:
            v2.extend(r)
        C2 = NU2
        for i in range(NV2 - 1):
            for j in range(C2 - 1):
                a = i * C2 + j
                f2.append((a, a + 1, a + C2 + 1, a + C2))
        cup = new_mesh_obj("AOI_Earcup_%s" % sfx, v2, f2)
        solidify(cup, 0.0040)
        for p in cup.data.polygons:
            p.use_smooth = True
        out.append(cup)
    return out


def build_ribbon():
    """Periwinkle ribbon binding the base of each twin tail."""
    out = []
    for sx, sfx in ((1, "R"), (-1, "L")):
        NU, NV = 16, 6
        rows = []
        for j in range(NV):
            v = -1 + 2 * j / (NV - 1)
            row = []
            for i in range(NU):
                u = -1 + 2 * i / (NU - 1)
                rr = math.sqrt(max(0.0, 1 - u * u))
                # small toroidal band around the tail base
                x = sx * (0.0930 + 0.0110 * math.cos(math.pi * v) * rr)
                y = 0.0430 + 0.0175 * u * rr
                z = 1.5720 + 0.0225 * v * rr
                row.append(Vector((x, y, z)))
            rows.append(row)
        v2, f2 = [], []
        for r in rows:
            v2.extend(r)
        C2 = NU
        for i in range(NV - 1):
            for j in range(C2 - 1):
                a = i * C2 + j
                f2.append((a, a + 1, a + C2 + 1, a + C2))
        rib = new_mesh_obj("AOI_Ribbon_%s" % sfx, v2, f2)
        solidify(rib, 0.0025)
        for p in rib.data.polygons:
            p.use_smooth = True
        out.append(rib)
    return out


def build_choker():
    """Thin choker band with a small metal ring at the front."""
    out = []
    NU, NV = 24, 6
    rows = []
    for j in range(NV):
        v = -1 + 2 * j / (NV - 1)
        row = []
        for i in range(NU):
            a = 2 * math.pi * i / NU
            rr = 0.0385 + 0.0022 * math.cos(math.pi * v)
            row.append(Vector((rr * math.sin(a),
                               rr * math.cos(a) + 0.0040,
                               1.3180 + 0.0045 * math.cos(math.pi * v))))
        rows.append(row)
    verts, faces = [], []
    for r in rows:
        verts.extend(r)
    C = NU
    for i in range(NV - 1):
        for j in range(C):
            a = i * C + j
            b = i * C + (j + 1) % C
            faces.append((a, b, b + C, a + C))
    ch = new_mesh_obj("AOI_Choker", verts, faces)
    solidify(ch, 0.0022)
    for p in ch.data.polygons:
        p.use_smooth = True
    out.append(ch)

    # small metal ring
    NU3, NV3 = 14, 6
    rows = []
    for j in range(NV3):
        v = -1 + 2 * j / (NV3 - 1)
        row = []
        for i in range(NU3):
            u = 2 * math.pi * i / NU3
            r = 0.0072 + 0.0018 * math.cos(math.pi * v)
            row.append(Vector((r * math.cos(u), -0.0395 - 0.0035 * math.cos(math.pi * v)
                               + 0.0060 * math.sin(u), 1.3160 + r * 0.92 * math.cos(u))))
        rows.append(row)
    v2, f2 = [], []
    for r in rows:
        v2.extend(r)
    C2 = NU3
    for i in range(NV3 - 1):
        for j in range(C2):
            a = i * C2 + j
            b = i * C2 + (j + 1) % C2
            f2.append((a, b, b + C2, a + C2))
    ring = new_mesh_obj("AOI_Choker_Ring", v2, f2)
    solidify(ring, 0.0016)
    for p in ring.data.polygons:
        p.use_smooth = True
    out.append(ring)
    return out


# --------------------------------------------------------------------------- #
def build_all():
    out = []
    out.append(build_top())
    out.append(build_jacket())
    out += build_jacket_trim()
    out.append(build_skirt())
    out.append(build_socks())
    out += list(build_shoe())
    out += build_headphones()
    out += build_ribbon()
    out += build_choker()
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import build_body
    build_body.build_all()
    for ob in build_all():
        print(" %-20s v=%5d f=%5d" % (ob.name, len(ob.data.vertices), len(ob.data.polygons)))
