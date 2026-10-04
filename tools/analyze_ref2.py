"""Region-by-region high-res ASCII + local palettes to understand the reference."""
import numpy as np
from PIL import Image

SRC = ".cloudforge/attachments/cmutfcqdl00b0pj1mwnhmjj75/file_00000000f53c8211ac65039906eb9733.png"
im = Image.open(SRC).convert("RGB")
a = np.asarray(im).astype(np.float32) / 255.0
H, W, _ = a.shape

RAMP = "@%#*+=-:. "

def show(arr, cols, title):
    hh, ww, _ = arr.shape
    rows = max(1, int(round(cols * hh / ww / 2.0)))
    sm = np.asarray(Image.fromarray((arr * 255).astype(np.uint8)).resize((cols, rows), Image.LANCZOS)) / 255.0
    lum = sm @ np.array([0.299, 0.587, 0.114])
    print(f"\n--- {title} ---")
    for r in range(rows):
        print("".join(RAMP[min(len(RAMP) - 1, int((1 - lum[r, c]) * (len(RAMP) - 1) * 1.2))] for c in range(cols)))

# global brightness statistics per horizontal band
print("=== PER-BAND MEAN COLOR (10 bands) ===")
for i in range(10):
    b = a[i * H // 10:(i + 1) * H // 10]
    m = (b.reshape(-1, 3).mean(0) * 255).astype(int)
    print(f"band {i} (y {i*H//10}-{(i+1)*H//10}): #{m[0]:02X}{m[1]:02X}{m[2]:02X}  maxlum={float((b@np.array([.299,.587,.114])).max()):.3f}")

show(a[0:627, 0:627], 96, "TOP-LEFT quadrant")
show(a[0:627, 627:1254], 96, "TOP-RIGHT quadrant")
show(a[627:1254, 0:627], 96, "BOTTOM-LEFT quadrant")
show(a[627:1254, 627:1254], 96, "BOTTOM-RIGHT quadrant")
