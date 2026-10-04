"""Master assembly: build the whole character, materials and UVs."""
import bpy
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_body
import build_face
import build_hair
import build_cloth
import textures as tex
from aoi_lib import weld

TEXDIR = "/tmp/aoi_tex"

# ---- object -> material mapping --------------------------------------------
# skin-bearing parts all share the skin material (separate objects, one slot)
SKIN_PARTS = {"AOI_Head", "AOI_Ear_R", "AOI_Ear_L", "AOI_Neck", "AOI_Torso",
              "AOI_Arm_R", "AOI_Arm_L", "AOI_Hand_R", "AOI_Hand_L",
              "AOI_Leg_R", "AOI_Leg_L", "AOI_Foot_R", "AOI_Foot_L",
              "AOI_Nose"}
FACE_PARTS = {"AOI_Mouth", "AOI_MouthLow"}
BROW_PARTS = {"AOI_Brow_R", "AOI_Brow_L"}
LASH_PARTS = {"AOI_Lash_R", "AOI_Lash_L"}
LASHLOW_PARTS = {"AOI_LashLow_R", "AOI_LashLow_L"}
EYEBALL_PARTS = {"AOI_Eye_R", "AOI_Eye_L"}
SOCKET_PARTS = {"AOI_EyeSocket_R", "AOI_EyeSocket_L"}
HAIR_PARTS = {"AOI_Hair_Scalp", "AOI_Hair_Back", "AOI_Hair_Bangs",
              "AOI_Hair_Bangs_L", "AOI_Hair_Side_R", "AOI_Hair_Side_L",
              "AOI_Hair_Tail_R", "AOI_Hair_Tail_L"}
OUTER_PARTS = {"AOI_Jacket"}
TRIM_PARTS = {"AOI_Jacket_Collar", "AOI_Jacket_Hem", "AOI_Ribbon_R",
              "AOI_Ribbon_L"}
INNER_PARTS = {"AOI_Top", "AOI_Sock_R", "AOI_Sock_L"}
DENIM_PARTS = {"AOI_Skirt"}
SHOE_PARTS = {"AOI_Shoe_R", "AOI_Shoe_L", "AOI_Sole_R", "AOI_Sole_L"}
METAL_PARTS = {"AOI_Headband_R", "AOI_Headband_L", "AOI_Earcup_R",
               "AOI_Earcup_L", "AOI_Choker_Ring"}
RUBBER_PARTS = {"AOI_Choker"}

MAT_ORDER = ["Skin", "Eye", "Hair", "Cloth_Outer", "Cloth_Trim", "Cloth_Inner",
             "Denim", "Shoe", "Metal", "Rubber", "Face", "Lash", "LashLow", "Brow"]


def make_materials():
    """Create the PBR materials and wire the generated textures to them."""
    M = {}

    def pbr(name, base_tex, rough_tex, rough=0.5, metal=0.0, normal=None, ao=None,
            ior=1.45, spec=0.5, sheen=0.0, subsurf=0.0):
        m = bpy.data.materials.new("M_" + name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        # a neutral base colour underneath, in case a texture fails to load
        bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = (1.0 if isinstance(metal, str)
                                                 else metal)
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = ior
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        if sheen and "Sheen Weight" in bsdf.inputs:
            bsdf.inputs["Sheen Weight"].default_value = sheen
            bsdf.inputs["Sheen Roughness"].default_value = 0.3
        if subsurf and "Subsurface Weight" in bsdf.inputs:
            bsdf.inputs["Subsurface Weight"].default_value = subsurf
            bsdf.inputs["Subsurface Radius"].default_value = (0.09, 0.035, 0.025)

        def tex_node(fname, kind, loc):
            path = os.path.join(TEXDIR, fname)
            if not fname or not os.path.exists(path):
                return None
            if kind not in bsdf.inputs:          # e.g. no AO socket on this shader
                return None
            img = bpy.data.images.load(path, check_existing=True)
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = img
            n.location = loc
            n.interpolation = 'Smart'
            n.extension = 'REPEAT'
            nt.links.new(n.outputs["Color"], bsdf.inputs[kind])
            return n

        tex_node(base_tex, "Base Color", (-700, 300))
        if rough_tex:
            tex_node(rough_tex, "Roughness", (-700, 50))
        if metal and isinstance(metal, str) and metal.endswith(".png"):
            tex_node(metal, "Metallic", (-700, -200))
        if normal:
            tex_node(normal, "Normal", (-700, -450))
        if ao:
            tex_node(ao, "AO", (-300, -650))
        return m

    M["Skin"] = pbr("Skin", "aoi_skin_basecolor.png", "aoi_skin_roughness.png",
                    normal="aoi_skin_normal.png", ao="aoi_skin_ao.png",
                    rough=0.55, spec=0.42, subsurf=0.22)
    M["Eye"] = pbr("Eye", "aoi_eye_basecolor.png", "aoi_eye_roughness.png",
                   normal="aoi_eye_normal.png", rough=0.18, spec=0.85)
    M["Hair"] = pbr("Hair", "aoi_hair_basecolor.png", "aoi_hair_roughness.png",
                    normal="aoi_hair_normal.png", rough=0.38, spec=0.6, sheen=0.35)
    M["Cloth_Outer"] = pbr("Cloth_Outer", "aoi_cloth_outer_basecolor.png",
                           "aoi_cloth_outer_roughness.png",
                           normal="aoi_cloth_outer_normal.png",
                           ao="aoi_cloth_outer_ao.png", rough=0.78)
    M["Cloth_Trim"] = pbr("Cloth_Trim", "aoi_cloth_trim_basecolor.png",
                          "aoi_cloth_trim_roughness.png",
                          normal="aoi_cloth_trim_normal.png", rough=0.74)
    M["Cloth_Inner"] = pbr("Cloth_Inner", "aoi_cloth_inner_basecolor.png",
                           "aoi_cloth_inner_roughness.png",
                           normal="aoi_cloth_inner_normal.png",
                           ao="aoi_cloth_inner_ao.png", rough=0.82)
    M["Denim"] = pbr("Denim", "aoi_denim_basecolor.png", "aoi_denim_roughness.png",
                     normal="aoi_denim_normal.png", ao="aoi_denim_ao.png",
                     rough=0.80)
    M["Shoe"] = pbr("Shoe", "aoi_shoe_basecolor.png", "aoi_shoe_roughness.png",
                    normal="aoi_shoe_normal.png", ao="aoi_shoe_ao.png", rough=0.55)
    M["Metal"] = pbr("Metal", "aoi_metal_basecolor.png", "aoi_metal_roughness.png",
                     metal="aoi_metal_metallic.png", normal="aoi_metal_normal.png",
                     rough=0.28)
    M["Rubber"] = pbr("Rubber", "aoi_rubber_basecolor.png",
                      "aoi_rubber_roughness.png",
                      normal="aoi_rubber_normal.png", rough=0.80)

    # --- small untextured accents, matched to the palette --------------------
    def flat(name, rgb, rough, metal=0.0, spec=0.5, sheen=0.0):
        m = bpy.data.materials.new("M_" + name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1.0)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = spec
        if sheen and "Sheen Weight" in b.inputs:
            b.inputs["Sheen Weight"].default_value = sheen
        return m

    M["Socket"] = flat("Socket", (0.965, 0.930, 0.935), 0.46, spec=0.5)
    M["Face"] = flat("Face", (0.855, 0.330, 0.360), 0.42, spec=0.6)
    M["Lash"] = flat("Lash", (0.075, 0.065, 0.105), 0.38, spec=0.6)
    M["LashLow"] = flat("LashLow", (0.300, 0.235, 0.285), 0.45)
    M["Brow"] = flat("Brow", (0.330, 0.245, 0.290), 0.58)
    return M


def material_group_of(name):
    """Which material group does this object belong to? (name -> group key)"""
    for parts, key in [(SKIN_PARTS, "Skin"), (EYEBALL_PARTS, "Eye"),
                       (HAIR_PARTS, "Hair"), (OUTER_PARTS, "Cloth_Outer"),
                       (TRIM_PARTS, "Cloth_Trim"), (INNER_PARTS, "Cloth_Inner"),
                       (DENIM_PARTS, "Denim"), (SHOE_PARTS, "Shoe"),
                       (METAL_PARTS, "Metal"), (RUBBER_PARTS, "Rubber"),
                       (FACE_PARTS, "Face"), (LASH_PARTS, "Lash"),
                       (LASHLOW_PARTS, "LashLow"), (BROW_PARTS, "Brow"),
                       (SOCKET_PARTS, "Socket")]:
        if name in parts:
            return key
    return "Unknown"


def assign_materials(M):
    groups = [(SKIN_PARTS, "Skin"), (SOCKET_PARTS, "Socket"),
              (EYEBALL_PARTS, "Eye"), (HAIR_PARTS, "Hair"),
              (OUTER_PARTS, "Cloth_Outer"), (TRIM_PARTS, "Cloth_Trim"),
              (INNER_PARTS, "Cloth_Inner"), (DENIM_PARTS, "Denim"),
              (SHOE_PARTS, "Shoe"), (METAL_PARTS, "Metal"),
              (RUBBER_PARTS, "Rubber"), (FACE_PARTS, "Face"),
              (LASH_PARTS, "Lash"), (LASHLOW_PARTS, "LashLow"),
              (BROW_PARTS, "Brow")]
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        mat = None
        for parts, key in groups:
            if ob.name in parts:
                mat = M[key]
                break
        ob.data.materials.clear()
        if mat:
            ob.data.materials.append(mat)


# --------------------------------------------------------------------------- #
#  UV unwrapping
# --------------------------------------------------------------------------- #
def uv_smart(ob, island_margin=0.004, angle=66.0, area_weight=0.0):
    """Angle-limited smart project, then pack with a real island margin."""
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle),
                             island_margin=island_margin,
                             area_weight=area_weight,
                             correct_aspect=True,
                             scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    return ob.data.uv_layers.active


def uv_face_eyes(ob, v0=0.24, v1=0.78):
    """Eye atlas UV: map the socket/cornea UV grid onto the eye texture region."""
    me = ob.data
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    us = [d.uv[0] for d in me.uv_layers.active.data] or []
    if not us:
        return
    umin, umax = min(us), max(us)
    for d in me.uv_layers.active.data:
        t = (d.uv[0] - umin) / max(1e-6, (umax - umin))
        d.uv = (v0 + t * (v1 - v0), 0.22 + d.uv[1] * 0.56)
    me.update()


def uv_front_fan(ob, u0=0.78, u1=0.999):
    """Hair region: push the UVs into a dedicated slab of the atlas."""
    me = ob.data
    if not me.uv_layers:
        return
    for d in me.uv_layers.active.data:
        t = d.uv[0]
        d.uv = (u0 + min(max(t, 0.0), 1.0) * (u1 - u0), d.uv[1])


# --------------------------------------------------------------------------- #
def build_character(with_uv=True):
    build_body.build_all()
    build_face.build_all()
    build_hair.build_all()
    build_cloth.build_all()

    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH':
            weld(ob)

    if with_uv:
        for ob in bpy.context.scene.objects:
            if ob.type != 'MESH':
                continue
            uv_smart(ob)

        # eyes get their dedicated atlas region
        for n in ("AOI_Eye_R", "AOI_Eye_L", "AOI_EyeSocket_R", "AOI_EyeSocket_L"):
            o = bpy.data.objects.get(n)
            if o:
                uv_face_eyes(o)
        return True
    return False


def stats():
    dg = bpy.context.evaluated_depsgraph_get()
    tris = verts = faces = 0
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        verts += len(me.vertices)
        faces += len(me.polygons)
        ev.to_mesh_clear()
    base_f = sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type == 'MESH')
    base_v = sum(len(o.data.vertices) for o in bpy.context.scene.objects if o.type == 'MESH')
    mats = set()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            for m in o.data.materials:
                if m:
                    mats.add(m.name)
    return dict(objects=len([o for o in bpy.context.scene.objects if o.type == 'MESH']),
                base_verts=base_v, base_faces=base_f,
                eval_verts=verts, eval_faces=faces, eval_tris=tris,
                materials=len(mats))


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tex.generate_all(TEXDIR)
    build_character()
    M = make_materials()
    assign_materials(M)
    s = stats()
    for k, v in s.items():
        print("  %-12s %s" % (k, v))
