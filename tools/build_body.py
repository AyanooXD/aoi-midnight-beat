"""Part 1 - body geometry for AOI. Head, ears, neck, torso, arms, hands, legs, feet."""
import bpy
import bmesh
import math
from mathutils import Vector
from aoi_lib import (new_mesh_obj, activate, activate_all, weld, subdivide, loft, loft_spine,
                     section, catmull_rom, shrink_loop, grid_surface, solidify,
                     mirror_dup, bevel, subsurf)

R = math.radians


# --------------------------------------------------------------------------- #
#  HEAD  —  UV-sphere deformed into an anime skull (flat-ish face plane, tapered chin)
# --------------------------------------------------------------------------- #
HEAD_CX, HEAD_CY, HEAD_CZ = 0.0, 0.010, 1.505
HEAD_RX, HEAD_RY, HEAD_RZ = 0.0840, 0.0930, 0.1250     # 0.250 tall, 0.168 wide


def head_t_from_z(z):
    """Exact inverse of the head's v mapping: chin t=0 -> crown t=1.

    The mapping is z = CZ - RZ*cos(pi*t), so the inverse is the arccos.
    """
    c = (HEAD_CZ - z) / HEAD_RZ
    c = max(-1.0, min(1.0, c))
    return math.acos(c) / math.pi


def head_surface(a, t):
    """A point ON the head surface. Every facial feature is placed with this so
    eyes/brows/nose/lash lines sit exactly on the skull instead of floating."""
    phi = math.pi * t
    s = 1.0 - 0.52 * max(0.0, (0.30 - t) / 0.30) ** 1.7      # chin taper
    w = 1.0 + 0.10 * math.sin(math.pi * min(1.0, t / 0.55))  # cheekbone
    xs = s * w
    d = abs(((a + math.pi) % (2 * math.pi)) - math.pi)
    flat = max(0.0, 1.0 - d / R(75))
    x = HEAD_RX * xs * math.sin(phi) * math.sin(a)
    y = HEAD_RY * xs * math.sin(phi) * math.cos(a)
    y = y * (1.0 - 0.16 * flat) + 0.010 * t
    z = HEAD_CZ - HEAD_RZ * math.cos(phi)
    return Vector((x, HEAD_CY + y, z))


def head_front(x, z, out=0.0):
    """Head-surface Y at a given (x, z), pushed `out` metres forward (toward -Y).

    Searches both hemispheres by |x| so the left and right sides are symmetric.
    """
    ax = abs(x)
    t = head_t_from_z(z)
    best, best_err = None, 1e9
    for i in range(1, 180):                 # 1 deg .. 179 deg, front hemisphere
        p = head_surface(R(i), t)
        err = abs(p.x - ax)
        if err < best_err:
            best_err, best = err, p
    return best.y - out


# --------------------------------------------------------------------------- #
#  HEAD  —  UV-sphere deformed into an anime skull (flat-ish face plane, tapered chin)
# --------------------------------------------------------------------------- #
def build_head():
    cx, cy, cz = HEAD_CX, HEAD_CY, HEAD_CZ
    U, V = 40, 32                            # u = around (seam at back), v = pole to pole

    # ---- silhouette shaping -------------------------------------------------
    verts = []
    for iv in range(V + 1):
        verts.extend(head_surface(2 * math.pi * (iu / U), iv / V) for iu in range(U))

    faces = []
    for iv in range(V):
        for iu in range(U):
            a0 = iv * U + iu
            a1 = iv * U + (iu + 1) % U
            b0 = (iv + 1) * U + iu
            b1 = (iv + 1) * U + (iu + 1) % U
            faces.append((a0, a1, b1, b0))

    ob = new_mesh_obj("AOI_Head", verts, faces)
    weld(ob)

    # ---- ear: build the RIGHT ear, then mirror it (guarantees symmetry) ------
    rows = []
    NR, NC = 9, 11
    for r in range(NR):
        s = r / (NR - 1)
        row = []
        for c in range(NC):
            u = c / (NC - 1)              # 0 front .. 1 back
            th = u * math.pi
            h = (s - 0.5) * 0.0455        # ear height
            cup = 0.0038 * (1 - math.cos(th)) * 0.5
            row.append(Vector((
                0.0745 + 0.0075 * math.sin(th),
                cy + 0.004 + 0.0135 * math.cos(th),
                1.4870 + h + cup * 0.25)))
        rows.append(row)
    ear = grid_surface("AOI_Ear_R", rows)
    solidify(ear, 0.0055)
    subdivide(ear, 1)
    ear.data.materials.clear()
    mirror_dup(ear, "AOI_Ear_L")

    # smooth shading everywhere
    for o in bpy.data.objects:
        if o.name.startswith("AOI_Head") or o.name.startswith("AOI_Ear"):
            for p in o.data.polygons:
                p.use_smooth = True
    return ob

# --------------------------------------------------------------------------- #
#  NECK
# --------------------------------------------------------------------------- #
def build_neck():
    keys = [(1.2680, 0.0345, 0.0350, -0.0020),
            (1.3050, 0.0330, 0.0335, -0.0015),
            (1.3400, 0.0345, 0.0360, 0.0010),
            (1.3750, 0.0410, 0.0425, 0.0040),
            (1.4050, 0.0455, 0.0460, 0.0045)]
    ob = loft_spine("AOI_Neck", keys, per_seg=3, ring_n=16)
    weld(ob)
    return ob


# --------------------------------------------------------------------------- #
#  TORSO  (bust + waist + hip profile, superellipse for a soft boxy ribcage)
# --------------------------------------------------------------------------- #
def build_torso():
    keys = [
        (1.4050, 0.0455, 0.0460, 0.0045),   # neck base
        (1.3500, 0.0620, 0.0545, 0.0040),   # upper chest
        (1.2950, 0.0800, 0.0605, 0.0030),   # shoulder line
        (1.2400, 0.0945, 0.0655, 0.0010),   # bust
        (1.1900, 0.0965, 0.0670, 0.0000),   # bust apex
        (1.1400, 0.0870, 0.0630, -0.0010),  # under bust
        (1.0800, 0.0760, 0.0585, -0.0020),  # waist
        (1.0300, 0.0755, 0.0590, -0.0020),  # waist (narrowest)
        (0.9850, 0.0830, 0.0640, -0.0010),  # hip
        (0.9400, 0.0900, 0.0670, 0.0000),   # widest hip
        (0.8950, 0.0885, 0.0665, 0.0010),
        (0.8600, 0.0800, 0.0620, 0.0020),   # crotch
    ]
    ob = loft_spine("AOI_Torso", keys, per_seg=4, ring_n=24, p=0.92)
    weld(ob)
    return ob


# --------------------------------------------------------------------------- #
#  ARM  (shoulder -> upper -> elbow -> fore -> wrist), slight A-pose
# --------------------------------------------------------------------------- #
ACROMION_X = 0.098
SHOULDER_Z = 1.290
ARM_TILT = 11.0          # degrees, A-pose
ARM_LEN = 0.415           # acromion -> wrist along the arm axis


def arm_transform(side):
    """Object transform that carries a downward limb into an A-pose."""
    sx = 1 if side > 0 else -1
    return (sx * ACROMION_X, 0.0, SHOULDER_Z), (0.0, R(-sx * ARM_TILT), 0.0)


def wrist_point(side):
    sx = 1 if side > 0 else -1
    th = R(-sx * ARM_TILT)
    x = -ARM_LEN * math.sin(th)
    z = -ARM_LEN * math.cos(th)
    return Vector((sx * ACROMION_X + x, 0.0, SHOULDER_Z + z))


def build_arm(side):
    sx = 1 if side > 0 else -1
    keys = [
        (0.0000, 0.0620, 0.0620, 0.0000),   # shoulder cap (local origin at acromion)
        (0.0000, 0.0600, 0.0610, 0.0000),
        (-0.0400, 0.0530, 0.0540, 0.0015),
        (-0.0900, 0.0445, 0.0455, 0.0030),   # mid upper arm
        (-0.1500, 0.0400, 0.0412, 0.0040),
        (-0.2100, 0.0372, 0.0384, 0.0045),   # elbow
        (-0.2650, 0.0392, 0.0398, 0.0040),
        (-0.3250, 0.0348, 0.0352, 0.0030),   # mid forearm
        (-0.3800, 0.0292, 0.0296, 0.0020),
        (-0.4150, 0.0252, 0.0258, 0.0015),   # wrist
    ]
    ob = loft_spine("AOI_Arm_%s" % ("R" if side > 0 else "L"), keys, per_seg=4, ring_n=16)
    weld(ob)
    loc, rot = arm_transform(side)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def build_hand(side):
    """Built for one side only and mirrored by the caller."""
    # palm: flattened loft, wrist at local z=0, fingers extending -Z
    keys = [
        (0.006, 0.0258, 0.0150, 0.0000),
        (-0.022, 0.0322, 0.0163, 0.0000),
        (-0.056, 0.0348, 0.0152, 0.0000),
        (-0.082, 0.0326, 0.0142, 0.0000),
    ]
    palm = loft_spine("AOI_Palm", keys, per_seg=4, ring_n=14)
    weld(palm)

    # fingers: 4 tapered tubes + thumb, rooted at the palm tip
    fdefs = [(-0.0300, 0.0150, 0.0620), (-0.0100, 0.0164, 0.0720),
             (0.0112, 0.0155, 0.0700), (0.0305, 0.0126, 0.0580)]
    parts = [palm]
    for i, (fx, r0, L) in enumerate(fdefs):
        fk = [(0.000, r0, r0 * 0.92, 0.000),
              (-L * 0.42, r0 * 0.92, r0 * 0.88, 0.000),
              (-L * 0.78, r0 * 0.78, r0 * 0.74, 0.000),
              (-L * 1.00, r0 * 0.40, r0 * 0.38, 0.000)]
        f = loft_spine("AOI_Finger_%d" % (i + 1), fk, per_seg=3, ring_n=10)
        weld(f)
        f.location = (fx, 0.0, -0.090)
        parts.append(f)

    tk = [(0.000, 0.0138, 0.0124, 0.000),
          (-0.024, 0.0118, 0.0104, 0.000),
          (-0.043, 0.0082, 0.0072, 0.000)]
    th = loft_spine("AOI_Thumb", tk, per_seg=3, ring_n=10)
    weld(th)
    th.location = (-0.0250, 0.0132, -0.036)
    th.rotation_euler = (0.0, R(58), R(38))      # splay the thumb outward too
    parts.append(th)

    activate_all(parts)
    bpy.ops.object.join()
    hand = bpy.context.object
    hand.name = "AOI_Hand_R"
    hand.data.name = hand.name
    weld(hand)
    # Wrist sits at the local origin and fingers run down -Z, so bake in the
    # A-pose tilt and drop the origin exactly onto the arm's wrist point.
    hand.rotation_euler = (0.0, R(-ARM_TILT), 0.0)
    activate(hand)
    bpy.ops.object.transform_apply(rotation=True, location=False, scale=False)
    hand.location = wrist_point(1)
    mirror_dup(hand, "AOI_Hand_L")
    return hand


# --------------------------------------------------------------------------- #
#  LEG  (hip -> thigh -> knee -> calf -> ankle)
# --------------------------------------------------------------------------- #
def build_leg(side):
    sx = 1 if side > 0 else -1
    keys = [
        (0.9500, 0.0700, 0.0740, 0.0000),   # hip / top thigh (inside torso)
        (0.9000, 0.0712, 0.0750, 0.0005),
        (0.8200, 0.0620, 0.0660, 0.0005),
        (0.7200, 0.0525, 0.0570, 0.0000),
        (0.6200, 0.0460, 0.0500, -0.0005),
        (0.5150, 0.0428, 0.0465, -0.0010),   # knee
        (0.4600, 0.0452, 0.0500, -0.0010),   # calf swell
        (0.3800, 0.0428, 0.0468, -0.0010),
        (0.2800, 0.0355, 0.0385, -0.0010),
        (0.1800, 0.0292, 0.0310, -0.0015),
        (0.1100, 0.0262, 0.0272, -0.0020),   # ankle
        (0.0800, 0.0268, 0.0276, -0.0020),
    ]
    ob = loft_spine("AOI_Leg_%s" % ("R" if side > 0 else "L"), keys, per_seg=4, ring_n=18)
    weld(ob)
    ob.location = (sx * 0.0455, 0.0010, 0.0)
    return ob


def build_foot(side):
    sx = 1 if side > 0 else -1
    # Foot built directly in world space: +Y is toward the heel, -Y toward the toe.
    keys = [
        (0.0620, 0.0290, 0.0300, 0.0340),    # ankle top (behind the shin)
        (0.0450, 0.0300, 0.0400, 0.0120),
        (0.0250, 0.0308, 0.0450, -0.0100),
        (0.0125, 0.0312, 0.0430, -0.0280),    # ball of the foot
        (0.0085, 0.0300, 0.0380, -0.0420),
        (0.0075, 0.0262, 0.0290, -0.0560),
        (0.0070, 0.0190, 0.0170, -0.0660),    # toe
        (0.0070, 0.0090, 0.0080, -0.0715),
    ]
    ob = loft_spine("AOI_Foot_%s" % ("R" if side > 0 else "L"), keys, per_seg=4, ring_n=14)
    weld(ob)
    ob.location = (sx * 0.0455, -0.0130, 0.0)
    return ob


# --------------------------------------------------------------------------- #
def build_all():
    parts = []
    parts.append(build_head())
    parts.append(build_neck())
    parts.append(build_torso())
    for s in (1, -1):
        parts.append(build_arm(s))
    parts.append(build_hand(1))          # builds R and mirrors to L
    for s in (1, -1):
        parts.append(build_leg(s))
        parts.append(build_foot(s))
    return parts


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ps = build_all()
    print("PARTS:", [o.name for o in ps])
    for o in ps:
        print(" %-22s verts=%5d faces=%5d" % (o.name, len(o.data.vertices), len(o.data.polygons)))
