"""Verify face features numerically by locating them in the check render."""
import numpy as np
from PIL import Image
import sys


def analyse(path, label):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(int)
    H, W, _ = a.shape

    def bbox(mask, name):
        if mask.sum() == 0:
            print("   %-10s : NOT FOUND" % name)
            return None
        ys, xs = np.where(mask)
        return (xs.min(), xs.max(), ys.min(), ys.max(), mask.sum())

    def near(c, tol=46):
        return (np.abs(a - np.array(c)).sum(2) < tol)

    feats = {
        'eye_blue':  (68, 120, 240),
        'lash_dark': (26, 23, 33),
        'brow':      (89, 66, 77),
        'mouth_red': (217, 82, 92),
        'skin':      (255, 209, 199),
    }

    print("\n=== %s (%dx%d) ===" % (label, W, H))
    res = {}
    for k, c in feats.items():
        m = near(c)
        res[k] = bbox(m, k)
        if res[k]:
            x0, x1, y0, y1, n = res[k]
            print("   %-10s : x[%4d..%4d] w=%4d | y[%4d..%4d] h=%4d | px=%d"
                  % (k, x0, x1, x1 - x0, y0, y1, y1 - y0, n))

    # ---- symmetry: compare the left/right halves of the colour features ----
    for k in ('eye_blue', 'lash_dark', 'brow'):
        m = near(feats[k])
        if m.sum() < 40:
            continue
        half = W // 2
        L = m[:, :half]
        R = m[:, half:][:, ::-1]
        overlap = (L & R).sum()
        union = (L | R).sum()
        iou = overlap / max(1, union)
        # also report the mirrored-centre offset
        ys, xs = np.where(m)
        cxr = xs.mean()
        print("   %-10s : mirror-IoU = %.3f  (1.0 = perfectly symmetric)"
              % (k, iou))

    # ---- eye vertical placement relative to the visible skin (head) --------
    sm = near(feats['skin'], 60)
    if sm.sum() > 100:
        ys, xs = np.where(sm)
        head_y0, head_y1 = ys.min(), ys.max()
        if res.get('eye_blue'):
            e = res['eye_blue']
            eye_cy = (e[2] + e[3]) / 2
            frac = (eye_cy - head_y0) / max(1, head_y1 - head_y0)
            print("   eye centre = %.1f%% up the visible skin span (target ~45-52%%)"
                  % (100 * frac))
        if res.get('mouth_red'):
            mo = res['mouth_red']
            mf = ((mo[2] + mo[3]) / 2 - head_y0) / max(1, head_y1 - head_y0)
            print("   mouth      = %.1f%% up (should be clearly below the eyes)"
                  % (100 * mf))
    return res


if __name__ == "__main__":
    for p, l in [("/tmp/face_f.png", "FACE FRONT"), ("/tmp/face_q.png", "FACE 3/4")]:
        analyse(p, l)
