"""Recover a perceivable view of the reference PNG via ASCII + color-class maps."""
import numpy as np
from PIL import Image
from collections import Counter

SRC = ".cloudforge/attachments/cmutfcqdl00b0pj1mwnhmjj75/file_00000000f53c8211ac65039906eb9733.png"
im = Image.open(SRC).convert("RGB")
print("SIZE", im.size)

a = np.asarray(im).astype(np.float32) / 255.0
h, w, _ = a.shape

# ---------- palette (k-means, no sklearn) ----------
from scipy.cluster.vq import kmeans2
flat = a.reshape(-1, 3)
data = flat[np.random.RandomState(0).choice(len(flat), 40000, replace=False)]
k = 14
cent, lab = kmeans2(data, k, minit='++', seed=0, iter=40)
counts = Counter(lab.tolist())
order = np.argsort([-counts[i] for i in range(k)])
print("\n=== DOMINANT COLORS ===")
for rank, i in enumerate(order):
    c = (cent[i] * 255).round().astype(int)
    print(f"{rank+1:2d}. #{c[0]:02X}{c[1]:02X}{c[2]:02X}  rgb({c[0]},{c[1]},{c[2]})  {100*counts[i]/len(lab):5.2f}%")

# ---------- luminance ascii of full image ----------
RAMP = "@%#*+=-:. "
def ascii_map(img_arr, cols):
    hh, ww, _ = img_arr.shape
    rows = max(1, int(round(cols * hh / ww / 2.1)))  # chars are ~2.1x tall
    small = np.asarray(Image.fromarray((img_arr * 255).astype(np.uint8)).resize((cols, rows), Image.LANCZOS)) / 255.0
    lum = small @ np.array([0.299, 0.587, 0.114])
    out = []
    for r in range(rows):
        line = "".join(RAMP[min(len(RAMP) - 1, int((1 - lum[r, c]) * (len(RAMP) - 1) * 1.15))] for c in range(cols))
        out.append(line)
    return "\n".join(out)

print("\n=== FULL IMAGE LUMINANCE MAP (100 cols) ===")
print(ascii_map(a, 100))

# ---------- color class map ----------
pal = (cent * 255).astype(int)
def classify(rgb):
    best, bi = 1e9, 0
    for i, c in enumerate(pal):
        d = ((rgb[0] - c[0]) ** 2 + (rgb[1] - c[1]) ** 2 + (rgb[2] - c[2]) ** 2)
        if d < best:
            best, bi = d, i
    return bi
labels = [classify(c) for c in pal]
chars = "ABCDEFGHIJKLMN"
print("\n=== COLOR CLASS LEGEND (each letter = one palette cluster) ===")
for i in range(k):
    c = pal[i]
    print(f"  {chars[i]} = #{c[0]:02X}{c[1]:02X}{c[2]:02X}   ({100*counts[i]/len(lab):.1f}%)")

cols, rows = 100, 50
small = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((cols, rows), Image.LANCZOS)).astype(np.uint8)
print("\n=== FULL IMAGE COLOR CLASS MAP ===")
for r in range(rows):
    print("".join(chars[classify(small[r, c])] for c in range(cols)))
