import bpy
import sys
sys.path.insert(0, ".")
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_body
build_body.build_all()
import audit
audit.audit("body")
