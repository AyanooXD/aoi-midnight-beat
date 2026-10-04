"""Render one preview per process invocation (keeps peak RAM low on a 2-core box)."""
import bpy
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio

OUT = "/tmp/aoi_previews"
BLEND = "/tmp/aoi_asset.blend"

VIEWS = {
    "front":   dict(yaw_deg=0,   pitch_deg=0,  dist=3.45, target=(0, 0, 0.86),   lens=85),
    "side":    dict(yaw_deg=90,  pitch_deg=0,  dist=3.45, target=(0, 0, 0.86),   lens=85),
    "back":    dict(yaw_deg=180, pitch_deg=0,  dist=3.45, target=(0, 0, 0.86),   lens=85),
    "face":    dict(yaw_deg=8,   pitch_deg=2,  dist=0.95, target=(0, 0, 1.500),  lens=85),
    "details": dict(yaw_deg=46,  pitch_deg=10, dist=0.82, target=(0.02, -0.02, 1.30), lens=70),
    "hero":    dict(yaw_deg=34,  pitch_deg=6,  dist=3.30, target=(0, 0, 0.88),   lens=80),
}
RES = {
    "front": (760, 1060), "side": (760, 1060), "back": (760, 1060),
    "face": (700, 840), "details": (700, 840), "hero": (820, 820),
}
# This sandbox is 2 cores / 4 GB: ~48 samples is the safe ceiling, so previews
# are rendered at 32-40 with Cycles denoising doing the rest of the work.
SAMPLES = {"hero": 40, "face": 36, "details": 32, "front": 36,
           "side": 28, "back": 28}


def main():
    which = sys.argv[1]
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    w, h = RES[which]
    cam = studio.build_studio(res=(w, h), samples=SAMPLES[which])
    # keep Cycles within a small memory budget on this 2-core / 4 GB sandbox
    sc = bpy.context.scene
    sc.cycles.use_auto_tile = True
    sc.cycles.tile_size = 128
    sc.cycles.debug_use_spatial_splits = False
    sc.cycles.use_persistent_data = False
    studio.place_cam(cam, **VIEWS[which])
    p = os.path.join(OUT, "%s.png" % which)
    t0 = time.time()
    studio.render(p, samples=SAMPLES[which])
    print("RENDERED %s in %.1fs -> %s (%d bytes)"
          % (which, time.time() - t0, p, os.path.getsize(p)))


if __name__ == "__main__":
    main()