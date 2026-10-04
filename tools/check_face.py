"""Face close-up check render with flat material colours."""
import bpy
import math
from mathutils import Vector

COL = {
    "AOI_Head": (1.00, 0.82, 0.78, 1), "AOI_Ear_L": (1.00, 0.82, 0.78, 1),
    "AOI_Ear_R": (1.00, 0.82, 0.78, 1), "AOI_Neck": (1.00, 0.82, 0.78, 1),
    "AOI_Torso": (1.00, 0.82, 0.78, 1),
    "AOI_Leg_L": (1.00, 0.82, 0.78, 1), "AOI_Leg_R": (1.00, 0.82, 0.78, 1),
    "AOI_Foot_L": (1.00, 0.82, 0.78, 1), "AOI_Foot_R": (1.00, 0.82, 0.78, 1),
    "AOI_Arm_L": (1.00, 0.82, 0.78, 1), "AOI_Arm_R": (1.00, 0.82, 0.78, 1),
    "AOI_Hand_L": (1.00, 0.82, 0.78, 1), "AOI_Hand_R": (1.00, 0.82, 0.78, 1),
    "AOI_Nose": (1.00, 0.82, 0.78, 1),
    "AOI_Mouth": (0.85, 0.32, 0.36, 1), "AOI_MouthLow": (0.92, 0.50, 0.52, 1),
    "AOI_Brow_L": (0.35, 0.26, 0.30, 1), "AOI_Brow_R": (0.35, 0.26, 0.30, 1),
    "AOI_Lash_L": (0.10, 0.09, 0.13, 1), "AOI_Lash_R": (0.10, 0.09, 0.13, 1),
    "AOI_LashLow_L": (0.30, 0.24, 0.28, 1), "AOI_LashLow_R": (0.30, 0.24, 0.28, 1),
    "AOI_EyeSocket_L": (0.97, 0.93, 0.93, 1), "AOI_EyeSocket_R": (0.97, 0.93, 0.93, 1),
    "AOI_Eye_L": (0.42, 0.47, 0.94, 1), "AOI_Eye_R": (0.42, 0.47, 0.94, 1),
}


def assign_flat():
    mats = {}
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        col = COL.get(ob.name, (0.7, 0.7, 0.7, 1))
        if col not in mats:
            m = bpy.data.materials.new("m_%d" % len(mats))
            m.diffuse_color = col
            m.use_nodes = True
            bsdf = m.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Base Color'].default_value = col
            bsdf.inputs['Roughness'].default_value = 0.45
            mats[col] = m
        ob.data.materials.clear()
        ob.data.materials.append(mats[col])


def face_cam(path, yaw=0.0, pitch=0.0, dist=0.42, target=(0, 0, 1.485), flat=True):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    # Standard view transform: pixel colour == material colour, no tone mapping.
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.display_settings.display_device = 'sRGB'
    sh = sc.display.shading
    sh.color_type = 'MATERIAL'
    if flat:
        # Flat + no highlights/shadows so pixel colour == material colour exactly.
        sh.light = 'FLAT'
        sh.show_shadows = False
        sh.show_specular_highlight = False
        sh.show_cavity = False
    else:
        sh.light = 'STUDIO'
        sh.show_shadows = True
        sh.show_shadows_intensity = 0.35
        sh.show_cavity = True
        sh.cavity_type = 'BOTH'
        sh.curvature_ridge_factor = 1.0
        sh.curvature_valley_factor = 1.0
    sc.render.resolution_x = sc.render.resolution_y = 900
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = path
    cd = bpy.data.cameras.new("C")
    cd.lens = 85
    cam = bpy.data.objects.new("C", cd)
    sc.collection.objects.link(cam)
    cam.location = (math.sin(yaw) * dist, -math.cos(yaw) * dist, target[2] + math.sin(pitch) * dist)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    bpy.ops.render.render(write_still=True)
    return cam
