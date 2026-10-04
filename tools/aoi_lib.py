"""Core procedural mesh helpers for the AOI character (Blender 4.2 / bpy)."""
import bpy
import math
import bmesh
from mathutils import Vector


# --------------------------------------------------------------------------- #
#  scene helpers
# --------------------------------------------------------------------------- #
def new_mesh_obj(name, verts, faces, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def activate(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    return ob


def activate_all(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]
    return objs


def weld(ob, dist=1e-5):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def subdivide(ob, cuts=1, smooth=0.0):
    activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=cuts, smoothness=smooth)
    bpy.ops.object.mode_set(mode='OBJECT')


def shrink_loop(ob, factor=0.88, z_axis=2, center=None):
    """Shrink the highest vertex loop inward — used to pinch limb caps."""
    me = ob.data
    zs = [v.co.z for v in me.vertices]
    zmax = max(zs)
    top = [v for v in me.vertices if v.co.z > zmax - 1e-4]
    c = Vector(center) if center else sum((v.co for v in top), Vector()) / len(top)
    for v in top:
        d = v.co - c
        v.co = c + d * factor
    me.update()


# --------------------------------------------------------------------------- #
#  Catmull-Rom + lofting  ->  all-quad tube surfaces
# --------------------------------------------------------------------------- #
def catmull_rom(pts, per_seg=6, closed=False):
    P = [Vector(p) for p in pts]
    if closed:
        ext = [P[-1]] + P + [P[0], P[1]]
        n = len(P)
    else:
        ext = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
        n = len(P) - 1
    out = []
    for i in range(n):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for s in range(per_seg):
            t = s / per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                              + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def section(cx, cy, z, w, d, y_off=0.0, p=1.0, n=16):
    """One elliptical cross-section: half-width w, half-depth d, superellipse power p."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        if p == 1.0:
            u, v = ca, sa
        else:
            u = math.copysign(abs(ca) ** p, ca)
            v = math.copysign(abs(sa) ** p, sa)
        pts.append(Vector((cx + w * u, cy + y_off + d * v, z)))
    return pts


def loft(name, sections, cap_start=True, cap_end=True, smooth=True):
    """Build an all-quad tube through a list of equal-length point rings."""
    n = len(sections[0])
    verts, faces = [], []
    for ring in sections:
        verts.extend(ring)
    for i in range(len(sections) - 1):
        a, b = i * n, (i + 1) * n
        for j in range(n):
            k = (j + 1) % n
            faces.append((a + j, a + k, b + k, b + j))
    if cap_start:
        c = sum((Vector(v) for v in verts[:n]), Vector()) / n
        verts.append(c)
        ci = len(verts) - 1
        for j in range(n):
            faces.append((ci, (j + 1) % n, j))
    if cap_end:
        off = (len(sections) - 1) * n
        c = sum((Vector(v) for v in verts[off:off + n]), Vector()) / n
        verts.append(c)
        ci = len(verts) - 1
        for j in range(n):
            faces.append((ci, off + j, off + (j + 1) % n))
    ob = new_mesh_obj(name, verts, faces)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def loft_spine(name, keys, per_seg=4, ring_n=16, p=1.0, **kw):
    """keys = [(z, half_width, half_depth, y_off), ...] -> lofted surface."""
    secs = [section(0.0, 0.0, z, w, d, y_off=yo, p=p, n=ring_n) for z, w, d, yo in keys]
    rings = []
    for i in range(per_seg * (len(secs) - 1) + 1):
        t = i / (per_seg * (len(secs) - 1))
        f = t * (len(secs) - 1)
        i0 = min(int(f), len(secs) - 2)
        u = f - i0
        a, b = secs[i0], secs[i0 + 1]
        rings.append([a[j].lerp(b[j], u) for j in range(ring_n)])
    return loft(name, rings, **kw)


# --------------------------------------------------------------------------- #
#  ribbons / cards / solidify
# --------------------------------------------------------------------------- #
def grid_surface(name, pts, close_u=False, thickness=0.0, smooth=True):
    """pts = list of rows, each row a list of points -> quad sheet."""
    rows, cols = len(pts), len(pts[0])
    verts = [p for row in pts for p in row]
    faces = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            a = i * cols + j
            faces.append((a, a + 1, a + cols + 1, a + cols))
    ob = new_mesh_obj(name, verts, faces)
    if close_u:
        # weld the two open side edges into a closed loop
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        for i in range(rows - 1):
            a = i * cols
            b = (i + 1) * cols
            bm.verts.ensure_lookup_table()
            bmesh.ops.remove_doubles(bm, verts=[bm.verts[a], bm.verts[b]], dist=1e-4)
        bm.to_mesh(me)
        bm.free()
    if thickness > 0:
        solidify(ob, thickness)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def solidify(ob, thickness, offset=0.0):
    """Give an open sheet thickness. bmesh-based, no edit-mode context needed."""
    _solidify_bmesh(ob, thickness, offset)
    weld(ob)


def _solidify_bmesh(ob, thickness, offset=0.0):
    """Deterministic bmesh solidify.

    The bpy.ops.mesh.solidify() operator exploded small closed shells (a 0.008 m
    choker ring came out spanning 6.7 m) because it depends on edit-mode context.
    Doing the offset explicitly from vertex normals is stable and testable.
    """
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    d = thickness * (0.5 - offset)
    geom = bmesh.ops.solidify(bm, geom=list(bm.faces) + list(bm.edges) + list(bm.verts))
    del geom
    # scale the freshly created shell along the vertex normals
    bm.normal_update()
    new_verts = [v for v in bm.verts if v.is_valid]
    for v in new_verts:
        v.co = v.co + v.normal * d
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def subsurf(ob, levels=1, render=2):
    m = ob.modifiers.new("Subdivision", 'SUBSURF')
    m.levels = levels
    m.render_levels = render
    return m


def bevel(ob, width=0.004, segments=2):
    m = ob.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = 0.7
    return m


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def mirror_dup(ob, name, axis='X'):
    """Duplicate an object mirrored across the WORLD plane X=0.

    Negative object scale only mirrors the local mesh; it leaves the world
    transform untouched, which silently puts the copy in the wrong place.
    So mirror both: invert the local matrix AND the location/rotation.
    """
    new = ob.copy()
    new.data = ob.data.copy()
    new.name = name
    new.data.name = name
    bpy.context.scene.collection.objects.link(new)

    i = {'X': 0, 'Y': 1, 'Z': 2}[axis]
    new.scale[i] *= -1.0
    if axis == 'X':
        new.location.x *= -1.0
        new.rotation_euler = (-new.rotation_euler.x,
                              -new.rotation_euler.y,
                              new.rotation_euler.z)

    activate(new)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    weld(new)
    # bake the mirror into the mesh so the object ends with a clean +1 scale
    bpy.ops.object.transform_apply(rotation=True, location=True, scale=True)
    return new


def move_to(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)
    return ob
