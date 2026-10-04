"""Check hair: does it hug the skull, and is the silhouette sane?"""
import bpy
from mathutils import Vector
from collections import defaultdict
from build_body import head_surface, head_t_from_z, HEAD_CX, HEAD_CY, HEAD_CZ


def radial_clearance(p):
    """Distance from the head's ellipsoid core, in metres."""
    dx = p.x - HEAD_CX
    dy = p.y - HEAD_CY
    dz = p.z - HEAD_CZ
    return max(abs(dx) / 0.084, abs(dy) / 0.093, abs(dz) / 0.125)


def report():
    objs = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
    hair = [n for n in objs if "Hair" in n or "Bang" in n]
    print("=== HAIR SHELL CLEARANCE OVER THE SKULL ===")
    for n in sorted(hair):
        pts = [objs[n].matrix_world @ v.co for v in objs[n].data.vertices]
        # only consider points that overlap the head region
        over = [p for p in pts if 1.34 < p.z < 1.68 and radial_clearance(p) < 1.25]
        if not over:
            print("  %-20s (no verts over the skull)" % n)
            continue
        d = [radial_clearance(p) for p in over]
        print("  %-20s n=%4d  clearance %.4f .. %.4f m"
              % (n, len(over), min(d), max(d)))

    print("\n=== HAIR EXTENTS ===")
    for n in sorted(hair):
        pts = [objs[n].matrix_world @ v.co for v in objs[n].data.vertices]
        print("  %-20s x[%+.3f,%+.3f] y[%+.3f,%+.3f] z[%+.3f,%+.3f]"
              % (n, min(p.x for p in pts), max(p.x for p in pts),
                 min(p.y for p in pts), max(p.y for p in pts),
                 min(p.z for p in pts), max(p.z for p in pts)))

    # does the fringe cover the eyes?
    print("\n=== FRINGE / EYE OCCLUSION ===")
    eyez = 1.490
    for n in ("AOI_Hair_Bangs", "AOI_Hair_Scalp"):
        if n not in objs:
            continue
        pts = [objs[n].matrix_world @ v.co for v in objs[n].data.vertices]
        low = [p for p in pts if p.y < -0.055 and abs(p.x) < 0.075]
        if low:
            print("  %-18s front verts below the eye line (z<%.3f): %d, lowest z=%.4f"
                  % (n, eyez, sum(1 for p in low if p.z < eyez),
                     min(p.z for p in pts if p.y < -0.055 and abs(p.x) < 0.075)))
    return True
