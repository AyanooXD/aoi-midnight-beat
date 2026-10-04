"""Build the finished asset and save it as a .blend for render + export stages."""
import bpy
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assemble
import textures as tex
from aoi_lib import weld

ASSET = "AOI_MIDNIGHT_BEAT"
TEXDIR = "/tmp/aoi_tex"
BLEND = "/tmp/aoi_asset.blend"


def tidy_names():
    """Normalise object + mesh names and sort them into readable order."""
    order = []
    for pre in ("Body", "Head", "Ear", "EyeSocket", "Eye", "Lash", "Brow",
                "Nose", "Mouth", "Neck", "Torso", "Arm", "Hand", "Leg", "Foot",
                "Hair_Scalp", "Hair_Back", "Hair_Bangs", "Hair_Side", "Hair_Tail",
                "Top", "Jacket", "Skirt", "Sock", "Shoe", "Sole",
                "Headband", "Earcup", "Ribbon", "Choker"):
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name.startswith("AOI_" + pre) and o not in order:
                order.append(o)
    # anything unexpected goes at the end so nothing is ever lost
    for o in bpy.data.objects:
        if o.type == 'MESH' and o not in order:
            order.append(o)
    return order


def apply_transforms():
    """Bake every object transform so the exported OBJ has clean world coords."""
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in meshes:
        if tuple(abs(v) for v in o.scale) != (1.0, 1.0, 1.0) or \
           tuple(o.rotation_euler) != (0, 0, 0) or tuple(o.location) != (0, 0, 0):
            bpy.context.view_layer.objects.active = o
            for s in bpy.context.selected_objects:
                s.select_set(False)
            o.select_set(True)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return meshes


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tex.generate_all(TEXDIR)
    assemble.build_character()
    M = assemble.make_materials()
    assemble.assign_materials(M)
    apply_transforms()
    for ob in tidy_names():
        weld(ob)
        if not ob.data.uv_layers:
            ob.data.uv_layers.new(name="UVMap")
    s = assemble.stats()
    print("=== ASSET BUILT ===")
    for k, v in s.items():
        print("   %-12s %s" % (k, v))
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("   saved:", BLEND)


if __name__ == "__main__":
    main()