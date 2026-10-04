"""Measure rendered subject brightness so studio lighting can be tuned by number."""
import numpy as np
from PIL import Image


def subject_stats(path, floor_ref=(0.055, 0.058, 0.070)):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114])

    # The floor is a large, smooth, near-uniform region: find it from the border.
    border = np.concatenate([lum[0, :], lum[-1, :], lum[:, 0], lum[:, -1]])
    f = np.median(border)
    floor_mask = np.abs(lum - f) < 0.035

    # subject = the connected non-floor mass in the centre
    H, W = lum.shape
    cx = W // 2
    col = lum[:, cx]
    rows = np.where(np.abs(col - f) > 0.05)[0]
    m = np.zeros_like(floor_mask)
    if len(rows):
        m[max(0, rows.min() - 4):min(H, rows.max() + 5), :] = True
    m &= ~floor_mask

    if m.sum() < 50:
        return dict(path=path, ok=False, note="no subject found")

    s = lum[m]
    p = np.percentile(s, [5, 25, 50, 75, 95])
    rgb = a[m].mean(0)
    return dict(path=path, ok=True,
                floor_lum=round(float(f), 4),
                subject_frac=round(float(m.mean()), 4),
                mean_lum=round(float(s.mean()), 4),
                p5=round(float(p[0]), 4), p25=round(float(p[1]), 4),
                p50=round(float(p[2]), 4), p75=round(float(p[3]), 4),
                p95=round(float(p[4]), 4),
                mean_rgb=[round(float(v), 4) for v in rgb])


def report(path):
    s = subject_stats(path)
    print("=== %s ===" % path.split('/')[-1])
    if not s.get("ok"):
        print("   ", s)
        return s
    print("    floor lum      %.4f" % s["floor_lum"])
    print("    subject covers %.1f%% of frame" % (100 * s["subject_frac"]))
    print("    subject mean L %.4f   (target 0.42 - 0.58)" % s["mean_lum"])
    print("    percentiles    p5=%.3f p25=%.3f p50=%.3f p75=%.3f p95=%.3f"
          % (s["p5"], s["p25"], s["p50"], s["p75"], s["p95"]))
    print("    mean RGB       %s" % s["mean_rgb"])
    verdict = "OK" if 0.36 <= s["mean_lum"] <= 0.62 else "** OUT OF RANGE **"
    print("    -> %s" % verdict)
    return s


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        report(p)
