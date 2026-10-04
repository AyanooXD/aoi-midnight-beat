"""Part 2 - facial features.

All features are built for the RIGHT side only and then mirrored across X, which
guarantees exact bilateral symmetry (mirroring earlier was the source of drift).
Every feature is placed using the real head surface, so nothing floats.
"""
import bpy
import math
from mathutils import Vector
from aoi_lib import new_mesh_obj, weld, solidify, mirror_dup
from build_body import head_surface, head_front, R

# --- feature landmarks (metres, world space) --------------------------------
CHIN_Z = 1.380
EYE_Z = 1.4900          # eye centre  -> 44% of head height (adult anime)
EYE_X = 0.0330
EYE_W = 0.0480          # full width
EYE_H = 0.0500          # full height
LASH_Z = 1.5145         # upper lash line, just above the eye top
BROW_Z = 1.5420
BROW_W = 0.0455
BROW_H = 0.0060
NOSE_Z = 1.4525
MOUTH_Z = 1.4175
MOUTH_W = 0.0300


def _on(x, z, out=0.0):
    return Vector((x, head_front(x, z), z))


def _eye_outline(u, v):
    """Superellipse outline -> rounded anime eye. u,v in [-1,1]."""
    e = 2.55
    a = math.copysign(abs(u) ** e, u) if u else 0.0
    b = math.copysign(abs(v) ** e, v) if v else 0.0
    n = (abs(a) ** 2 + abs(b) ** 2) ** 0.5 or 1.0
    return a / n, b / n


# --------------------------------------------------------------------------- #
#  EYE  —  concave sclera patch + convex cornea carrying the iris
# --------------------------------------------------------------------------- #
def _socket_patch(name):
    NU, NV = 15, 15
    rows = []
    for j in range(NV):
        v = -1 + 2 * j / (NV - 1)
        row = []
        for i in range(NU):
            u = -1 + 2 * i / (NU - 1)
            lx, lz = _eye_outline(u, v)
            x = EYE_X + lx * EYE_W * 0.5
            z = EYE_Z + lz * EYE_H * 0.5
            p = _on(x, z)
            dish = (1 - u * u) * (1 - v * v)
            p.y += 0.0095 * dish                 # dish inward -> real socket
            row.append(p)
        rows.append(row)
    return _sheet(name, rows, 0.0016)


def _cornea(name):
    """Convex bulge that sits proud of the dish -> gives the eye real volume."""
    NU, NV = 19, 17
    r = 0.0230
    rows = []
    for j in range(NV):
        v = -1 + 2 * j / (NV - 1)
        row = []
        for i in range(NU):
            u = -1 + 2 * i / (NU - 1)
            lx, lz = _eye_outline(u, v)
            x = EYE_X + lx * EYE_W * 0.5
            z = EYE_Z + lz * EYE_H * 0.5
            base = _on(x, z)
            k = max(0.0, 1.0 - (u * u) * 0.80 - (v * v) * 0.80)
            row.append(Vector((x, base.y - r * math.sqrt(k), z)))
        rows.append(row)
    return _sheet(name, rows, 0.0010)


def _sheet(name, rows, thick):
    verts, faces = [], []
    for r in rows:
        verts.extend(r)
    C = len(rows[0])
    for i in range(len(rows) - 1):
        for j in range(C - 1):
            a = i * C + j
            faces.append((a, a + 1, a + C + 1, a + C))
    ob = new_mesh_obj(name, verts, faces)
    solidify(ob, thick)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


# --------------------------------------------------------------------------- #
#  strips: lash lines, brows, lips
# --------------------------------------------------------------------------- #
def _strip(name, pts, width, thick, taper=True):
    rows = []
    n = len(pts)
    for i, (x, z) in enumerate(pts):
        if i == 0:
            dx, dz = pts[1][0] - x, pts[1][1] - z
        elif i == n - 1:
            dx, dz = x - pts[-2][0], z - pts[-2][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dz = pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dz) or 1.0
        nx, nz = -dz / L, dx / L
        t = 1.0
        if taper:
            e = min(i, n - 1 - i) / max(1.0, (n - 1) * 0.45)
            t = 0.30 + 0.70 * min(1.0, e)
        w = width * (0.42 + 0.58 * t) * 0.5
        p = _on(x, z)
        rows.append([Vector((p.x + nx * w, p.y + 0.0004, p.z + nz * w)),
                     Vector((p.x - nx * w, p.y + 0.0004, p.z - nz * w))])
    verts, faces = [], []
    for r in rows:
        verts.extend(r)
    for i in range(len(rows) - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    ob = new_mesh_obj(name, verts, faces)
    solidify(ob, thick)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def _lash():
    pts = []
    steps = 18
    for i in range(steps):
        lx = -0.55 + 1.10 * (i / (steps - 1))      # -0.55 inner .. +0.55 outer
        x = EYE_X + lx * EYE_W * 0.52
        # rises over the eye centre, flicks up at the OUTER corner
        z = LASH_Z + 0.0055 * (1 - (lx / 0.55) ** 2) - 0.0060 * lx
        pts.append((x, z))
    return _strip("AOI_Lash_R", pts, 0.0085, 0.0022)


def _lash_low():
    pts = []
    steps = 14
    for i in range(steps):
        lx = -0.42 + 0.84 * (i / (steps - 1))
        x = EYE_X + lx * EYE_W * 0.48
        z = EYE_Z - EYE_H * 0.5 + 0.0042
        pts.append((x, z))
    return _strip("AOI_LashLow_R", pts, 0.0034, 0.0014)


def _brow():
    pts = []
    steps = 16
    for i in range(steps):
        lx = -0.55 + 1.10 * (i / (steps - 1))
        x = EYE_X + lx * BROW_W
        arc = 0.0090 * max(0.0, 1 - (lx + 0.10) ** 2 * 1.7)
        z = BROW_Z + arc - 0.0062 * lx            # inner end lower, outer higher
        pts.append((x, z))
    return _strip("AOI_Brow_R", pts, BROW_H, 0.0018)


def _nose():
    rows = []
    NR = 8
    for i in range(NR):
        t = i / (NR - 1)
        z = NOSE_Z + 0.0105 - t * 0.0170
        halfw = 0.0058 * math.sin(math.pi * t) + 0.0013
        yb = head_front(0.0, z)
        row = []
        for k in range(5):
            u = k / 4 * 2 - 1
            row.append(Vector((u * halfw,
                               yb - 0.0018 * (1 - u * u) * math.sin(math.pi * t)
                               - 0.0026 * t, z)))
        rows.append(row)
    return _sheet("AOI_Nose", rows, 0.0040)


def _lips():
    out = []
    pts = []
    steps = 19
    for i in range(steps):
        u = -1 + 2 * i / (steps - 1)
        pts.append((u * MOUTH_W * 0.5, MOUTH_Z - 0.0040 * u * u))
    out.append(_strip("AOI_Mouth", pts, 0.0042, 0.0026))
    out.append(_strip("AOI_MouthLow", [(x, z - 0.0040) for x, z in pts], 0.0052, 0.0030))
    return out


# --------------------------------------------------------------------------- #
def build_all():
    """Returns all face objects; right-side ones are mirrored automatically."""
    right = [_socket_patch("AOI_EyeSocket_R"), _cornea("AOI_Eye_R"),
             _lash(), _lash_low(), _brow(), _nose()]
    right += _lips()

    out = list(right)
    for ob in right:
        if ob.name.endswith("_R"):
            out.append(mirror_dup(ob, ob.name[:-2] + "_L"))
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import build_body
    build_body.build_all()
    obs = build_all()
    import verify_geom
    verify_geom.report()
