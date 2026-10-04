"""Quick viewport-style check render of whatever geometry exists (Workbench, fast)."""
import bpy
import math
import sys
from mathutils import Vector


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def setup(scene_objects, out, res=(420, 700), ortho=True, samples=12):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'SINGLE'
    sc.display.shading.single_color = (0.55, 0.57, 0.62)
    sc.display.shading.show_cavity = True
    sc.display.shading.show_shadows = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = out

    cam_d = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    if ortho:
        cam_d.type = 'ORTHO'
        cam_d.ortho_scale = 1.85
    cam.location = (0, -6, 0.85)
    look_at(cam, (0, 0, 0.85))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0, ".")
    import build_body
    build_body.build_all()
    setup(None, "/tmp/chk_front.png")
    sc = bpy.context.scene
    sc.render.filepath = "/tmp/chk_side.png"
    sc.camera.location = (6, 0, 0.85)
    from aoi_lib import activate
    import mathutils
    d = mathutils.Vector((0, 0, 0.85)) - sc.camera.location
    sc.camera.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.render.render(write_still=True)
    print("DONE")
