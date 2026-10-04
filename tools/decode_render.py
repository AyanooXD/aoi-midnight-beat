"""Decode a render against the DESIGN palette: where does each material appear?"""
import numpy as np
from PIL import Image
import sys

PAL = {
    "skin":    ("#F2C9BC", "skin"),
    "hair":    ("#2E2A3A", "hair"),
    "hairtip": ("#8E86BE", "hair tip"),
    "jacket":  ("#262B3C", "jacket"),
    "accent":  ("#7C85F3", "periwinkle accent"),
    "inner":   ("#EDE9EE", "off-white cloth"),
    "skirt":   ("#1B2030", "skirt"),
    "shoe":    ("#232838", "shoe upper"),
    "floor":   ("#2A2C33", "studio floor"),
    "metal":   ("#B9BCC9", "metal"),
}
CHAR = {"skin", "hair", "hairtip", "jacket", "accent", "inner", "skirt", "shoe", "metal"}


def hx(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def decode(path, crop=True):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0
    keys = list(PAL)
    P = np.stack([hx(PAL[k][0]) for k in keys])
    d = np.abs(a[:, :, None, :] - P[None, None, :, :]).sum(-1)
    idx = d.argmin(-1)
    lab = np.array(keys)[idx]
    err = d.min(-1)

    if crop:
        # restrict to the subject: exclude the floor (most common at borders)
        m = np.ones_like(lab, dtype=bool)
        floor = lab == "floor"
        # subject = pixels in the central column band that are not floor
        H, W = lab.shape
        cx = W // 2
        col = lab[:, cx]
        subj_rows = np.where(col != "floor")[0]
        if len(subj_rows):
            m[:max(0, subj_rows.min() - 5), :] = False
            m[min(H, subj_rows.max() + 6):, :] = False
        # also crop horizontally to the subject's widest extent
        band = lab[m]
        m[:] = m
    else:
        m = np.ones_like(lab, dtype=bool)

    print("=== %s ===" % path)
    print("  whole frame:")
    tot = lab.size
    for k in keys:
        n = int((lab == k).sum())
        if n / tot > 0.002:
            print("     %-8s %-18s %6.2f%%" % (k, PAL[k][1], 100 * n / tot))
    print("  subject band:")
    n = int(m.sum())
    for k in keys:
        c = int(((lab == k) & m).sum())
        if c / max(1, n) > 0.004:
            print("     %-8s %-18s %6.2f%%" % (k, PAL[k][1], 100 * c / max(1, n)))
    return lab, m


def ascii_map(path, cols=110, rows=None):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0
    h, w, _ = a.shape
    rows = rows or max(1, int(cols * h / w / 2.1))
    small = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((cols, rows), Image.LANCZOS)).astype(np.float32) / 255.0
    lum = small @ np.array([0.299, 0.587, 0.114])
    RAMP = "@%#*+=-:. "
    out = []
    for r in range(rows):
        out.append("".join(RAMP[min(9, int((1 - lum[r, c]) * 10 * 1.2))] for c in range(cols)))
    return "\n".join(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        decode(p)
