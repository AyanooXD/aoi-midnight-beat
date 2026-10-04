import bpy, sys, os, time
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 16
sc.render.resolution_x = 160
sc.render.resolution_y = 160
sc.render.filepath = '/tmp/smoke.png'
sc.render.image_settings.file_format = 'PNG'
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 0))
bpy.ops.object.shade_smooth()
# materials + textures + UV
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -1.2))
m = bpy.data.materials.new("M"); m.use_nodes = True
bsdf = m.node_tree.nodes['Principled BSDF']
tex = m.node_tree.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 8
os.makedirs('/tmp/tex', exist_ok=True)
from PIL import Image as PILImage
PILImage.new('RGBA', (64, 64), (128, 200, 255, 255)).save('/tmp/tex/t.png')
bpy.data.images.load('/tmp/tex/t.png', check_existing=True)
nt = m.node_tree; nt.links.new(tex.outputs['Fac'], bsdf.inputs['Roughness'])
bpy.context.object.data.materials.append(m)
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project()
bpy.ops.object.mode_set(mode='OBJECT')
w = bpy.data.objects.new("L", bpy.data.lights.new("L", 'SUN')); sc.collection.objects.link(w)
w.rotation_euler = (0.6, 0.2, 0.3); w.data.energy = 4
cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d); sc.collection.objects.link(cam)
cam.location = (0, -5, 1.2); cam.rotation_euler = (1.4, 0, 0); sc.camera = cam
t0 = time.time()
bpy.ops.render.render(write_still=True)
print("RENDER OK %.2fs" % (time.time() - t0), os.path.getsize('/tmp/smoke.png'), "bytes")
print("SMOKE TEST PASSED")
