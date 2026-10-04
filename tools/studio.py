"""Studio lighting + camera rig + Cycles preview renderer."""
import bpy
import math
import os
from mathutils import Vector


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.size = size
    ld.energy = energy
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    return ob


def build_studio(res=(1200, 1600), samples=96, floor=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False

    # clean, softly-lit neutral studio
    world = bpy.data.worlds.new("Studio")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.150, 0.162, 0.195, 1.0)
    bg.inputs[1].default_value = 1.0

    T = (0, 0, 0.86)
    area("Key", (-1.55, -1.85, 1.95), T, 2.0, 1150, (1.0, 0.97, 0.94))
    area("Fill", (2.05, -1.30, 1.10), T, 2.6, 420, (0.90, 0.94, 1.0))
    area("Rim", (0.70, 2.30, 1.95), T, 1.6, 1350, (0.86, 0.90, 1.0))
    area("Bounce", (0.0, -1.10, -0.15), T, 3.0, 210, (1.0, 1.0, 1.0))
    area("FaceLight", (0.0, -0.95, 1.62), (0, 0, 1.50), 0.8, 190, (1.0, 0.98, 0.97))
    # dedicated facial key so close-ups stay readable
    area("FaceKey", (-0.45, -0.72, 1.60), (0, 0.02, 1.505), 0.55, 260, (1.0, 0.98, 0.96))
    area("FaceFill", (0.52, -0.60, 1.50), (0, 0.02, 1.505), 0.55, 120, (0.94, 0.96, 1.0))

    if floor:
        me = bpy.data.meshes.new("Floor")
        me.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [],
                       [(0, 1, 2, 3)])
        me.update()
        fl = bpy.data.objects.new("StudioFloor", me)
        sc.collection.objects.link(fl)
        m = bpy.data.materials.new("M_Floor")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.085, 0.090, 0.105, 1)
        b.inputs["Roughness"].default_value = 0.38
        fl.data.materials.append(m)
        # shadow catcher so the floor reads as a clean studio sweep
        fl.is_shadow_catcher = False

    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam_d.lens = 85
    cam_d.sensor_width = 36
    return cam


def place_cam(cam, yaw_deg, pitch_deg=0.0, dist=5.2, target=(0, 0, 0.86), lens=85,
              ortho=None):
    """Camera on a sphere around the target. yaw 0 = front (-Y)."""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    cam.location = (math.sin(y) * math.cos(p) * dist,
                    -math.cos(y) * math.cos(p) * dist,
                    target[2] + math.sin(p) * dist)
    look_at(cam, target)
    cam.data.lens = lens
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'
    return cam


def render(path, samples=None):
    sc = bpy.context.scene
    if samples:
        sc.cycles.samples = samples
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
