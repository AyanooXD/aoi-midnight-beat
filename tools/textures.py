"""Original, fully procedural PBR texture generation (numpy + PIL only).

Every map here is synthesised from noise/height fields written for this asset.
No external image, scan or third-party texture is used anywhere in this file.
"""
import os
import numpy as np
from PIL import Image

OUT = None            # set by caller


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def fbm(h, w, octaves=5, base=4, persist=0.55, seed=0):
    """Fractal value noise via bicubic-upsampled random lattices."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        f = base * (2 ** o)
        small = rng.random((max(2, int(f)), max(2, int(f)))).astype(np.float32)
        up = np.asarray(Image.fromarray((small * 255).astype(np.uint8))
                        .resize((w, h), Image.BICUBIC), np.float32) / 255.0
        out += up * amp
        total += amp
        amp *= persist
    return out / total


def height_to_normal(hgt, strength=1.0):
    """Sobel-gradient normal map from a height field. Returns RGB uint8."""
    h, w = hgt.shape
    gy, gx = np.gradient(hgt.astype(np.float32))
    scale = strength * 6.0
    nx = -gx * scale
    ny = -gy * scale
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    rgb = np.stack([(nx * 0.5 + 0.5), (ny * 0.5 + 0.5), (nz * 0.5 + 0.5)], -1)
    return (rgb * 255).clip(0, 255).astype(np.uint8)


def ao_from_height(hgt, radius=9):
    """Cheap cavity AO: darken where the height field is locally concave."""
    from scipy.ndimage import gaussian_filter
    blur = gaussian_filter(hgt.astype(np.float32), radius)
    d = hgt - blur                       # >0 convex, <0 concave
    ao = np.clip(0.5 - d * 6.0, 0.0, 1.0)
    return ao


def save(arr_rgb, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    Image.fromarray(arr_rgb.astype(np.uint8), "RGB").save(p, optimize=True)
    return p


def save_gray(arr, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "L").save(p, optimize=True)
    return p


def hx(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


# --------------------------------------------------------------------------- #
#  material generators
# --------------------------------------------------------------------------- #
def gen_skin(size=1024):
    """Soft skin: subtle pores + very low-frequency blotching. Base + rough + nrm + ao.

    Albedo is kept reasonably high (real skin is ~0.35-0.45 linear) so the
    character does not go black under studio lighting.
    """
    h = w = size
    pores = fbm(h, w, octaves=6, base=24, persist=0.6, seed=11)
    blotch = fbm(h, w, octaves=3, base=3, persist=0.5, seed=12)
    hgt = pores * 0.35 + blotch * 0.65

    base = hx("F7D4C8")[None, None, :] * np.ones((h, w, 1), np.float32)
    tint = hx("E0A79C")[None, None, :]
    m = (blotch - 0.5)[..., None] * 0.14
    rgb = np.clip(base * (1 + m) + tint * np.clip(-m, 0, None) * 0.9, 0, 1)

    rough = np.clip(0.52 + (pores - 0.5) * 0.18 + (blotch - 0.5) * 0.10, 0.30, 0.78)
    save(rgb, "aoi_skin_basecolor.png")
    save_gray(rough, "aoi_skin_roughness.png")
    save(height_to_normal(hgt, 0.35), "aoi_skin_normal.png")
    save_gray(ao_from_height(hgt, 14), "aoi_skin_ao.png")
    return "aoi_skin_basecolor.png"


def gen_hair(size=1024):
    """Hair: deep midnight base with a periwinkle tip gradient + strand striations."""
    h = w = size
    strand = fbm(h, w, octaves=5, base=40, persist=0.62, seed=21)
    # stretch the noise vertically so it reads as strands
    ys = np.linspace(0, 1, h)[:, None]
    xs = np.linspace(0, 1, w)[None, :]
    wave = 0.5 + 0.5 * np.sin(xs * 150.0 + strand * 9.0 + ys * 5.0)
    fine = fbm(h, w, octaves=4, base=90, persist=0.5, seed=22)

    grad = np.clip(ys + 0.10 * (strand - 0.5), 0, 1)          # v: root -> tip
    root = hx("453F5C")[None, None, :]
    mid = hx("6E67A0")[None, None, :]
    tip = hx("A79ED6")[None, None, :]
    rgb = np.where((grad < 0.55)[..., None],
                   root + (mid - root) * (grad / 0.55)[..., None],
                   mid + (tip - mid) * ((grad - 0.55) / 0.45)[..., None])
    sh = (wave - 0.5)[..., None] * 0.10 + (fine - 0.5)[..., None] * 0.05
    rgb = np.clip(rgb * (1 + sh), 0, 1)

    rough = np.clip(0.34 + (1 - wave) * 0.16 + (fine - 0.5) * 0.08, 0.20, 0.62)
    hgt = wave * 0.7 + fine * 0.3
    save(rgb, "aoi_hair_basecolor.png")
    save_gray(rough, "aoi_hair_roughness.png")
    save(height_to_normal(hgt, 0.55), "aoi_hair_normal.png")
    save_gray(ao_from_height(hgt, 6), "aoi_hair_ao.png")
    return "aoi_hair_basecolor.png"


def gen_eye(size=2048):
    """One atlas containing sclera + iris + pupil + highlights.

    Socket and cornea share identical UVs, so this single image lines up
    across both and the convex cornea reads as the glossy iris.
    """
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / (w - 1)
    v = yy / (h - 1)
    dx = (u - 0.5)
    dy = (v - 0.5)
    r = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)

    # ---- sclera -----------------------------------------------------------
    rgb = np.ones((h, w, 3), np.float32) * np.array(hx("FBF7F8"), np.float32)
    corner = np.clip((np.abs(dx) - 0.26) / 0.24, 0, 1)
    rgb -= (corner ** 2)[..., None] * np.array(hx("E8C4C0"), np.float32) * 0.55
    lash_shade = np.clip((0.16 - v) / 0.16, 0, 1) ** 1.5
    rgb *= (1 - 0.28 * lash_shade)[..., None]

    # ---- iris -------------------------------------------------------------
    IR = 0.300                       # iris radius in UV units (half-width)
    fib = fbm(h, w, octaves=5, base=70, persist=0.55, seed=31)
    # radial fibres: angular modulation of the noise gives a fibre-like pattern
    radial = 0.5 + 0.5 * np.sin(ang * 64.0 + fib * 12.0)
    radial = radial * 0.55 + fib * 0.45

    iris_mask = np.clip((IR - r) / 0.012, 0, 1)
    iris_c = np.where((r / IR)[..., None] < 0.72,
                      hx("3A44A8")[None, None, :],
                      hx("6E7BF0")[None, None, :])
    iris_c = iris_c * (0.72 + 0.55 * radial[..., None])
    # bright limbal ring
    ring = np.clip(1 - np.abs(r / IR - 0.93) / 0.09, 0, 1)
    iris_c += ring[..., None] * hx("9AA6FF")[None, None, :] * 0.55
    # dark pupil
    PR = IR * 0.44
    pupil = np.clip((PR - r) / 0.008, 0, 1)
    iris_c = iris_c * (1 - pupil[..., None] * 0.96)
    # lower iris glow (anime style)
    iris_c += np.clip((v - 0.5) * 2.4, 0, 1)[..., None] * 0.14 * iris_mask[..., None]

    rgb = rgb * (1 - iris_mask[..., None]) + iris_c * iris_mask[..., None]

    # ---- highlights -------------------------------------------------------
    hl = np.zeros((h, w), np.float32)
    for cx, cy, rad, amt in ((-0.085, -0.115, 0.062, 0.95),
                             (0.075, 0.115, 0.030, 0.70),
                             (0.140, -0.030, 0.018, 0.45)):
        d = np.sqrt((u - (0.5 + cx)) ** 2 + (v - (0.5 + cy)) ** 2)
        hl = np.clip(hl + np.clip(1 - d / rad, 0, 1) * amt, 0, 1)
    rgb = rgb * (1 - hl[..., None] * 0.92) + hl[..., None] * 1.0

    # ---- roughness: highlights glossy, iris glossy, sclera matte-ish -------
    rough = np.clip(0.30 + lash_shade * 0.10 - iris_mask * 0.06 - hl * 0.24, 0.06, 0.45)

    save(rgb, "aoi_eye_basecolor.png")
    save_gray(rough, "aoi_eye_roughness.png")
    # flat normal: the eyeball's curvature is real geometry, not a normal map
    save(height_to_normal(np.zeros((h, w), np.float32), 0.0), "aoi_eye_normal.png")
    return "aoi_eye_basecolor.png"


def _cloth_set(prefix, col, weave_seed, rough_base=0.72, weave=150, ribbed=False,
               lift=1.0):
    h = w = 1024
    n = fbm(h, w, octaves=5, base=64, persist=0.55, seed=weave_seed)
    xs = np.linspace(0, 1, w)[None, :]
    ys = np.linspace(0, 1, h)[:, None]
    if ribbed:
        hgt = 0.5 + 0.5 * np.sin(xs * weave)
        hgt = 0.65 * hgt + 0.35 * n
    else:
        wx = 0.5 + 0.5 * np.sin(xs * weave)
        wy = 0.5 + 0.5 * np.sin(ys * weave)
        hgt = 0.45 * (wx * wy) + 0.35 * n
    base = hx(col)[None, None, :] * np.ones((h, w, 1), np.float32) * lift
    shade = (hgt - hgt.mean())[..., None] * 0.30
    rgb = np.clip(base * (1 + shade), 0, 1)
    rough = np.clip(rough_base + (n - 0.5) * 0.16, 0.35, 0.95)
    save(rgb, prefix + "_basecolor.png")
    save_gray(rough, prefix + "_roughness.png")
    save(height_to_normal(hgt, 0.5), prefix + "_normal.png")
    save_gray(ao_from_height(hgt, 7), prefix + "_ao.png")


def gen_cloth():
    # `lift` keeps dark garments readable instead of crushing to black.
    _cloth_set("aoi_cloth_outer", "3C445C", 41, lift=1.35)          # bomber jacket
    _cloth_set("aoi_cloth_trim", "8B93F5", 42, ribbed=True)        # periwinkle rib
    _cloth_set("aoi_cloth_inner", "F2EFF4", 43, lift=1.05)         # top + socks
    _cloth_set("aoi_denim", "4A5478", 44, lift=1.30)               # skirt twill


def gen_shoe(size=1024):
    h = w = size
    n = fbm(h, w, octaves=6, base=70, persist=0.6, seed=51)
    cells = fbm(h, w, octaves=4, base=34, persist=0.5, seed=52)
    hgt = cells * 0.7 + n * 0.3
    base = hx("39405C")[None, None, :] * np.ones((h, w, 1), np.float32)
    rgb = np.clip(base * (0.85 + 0.35 * hgt[..., None]), 0, 1)
    rough = np.clip(0.44 + (n - 0.5) * 0.20, 0.25, 0.75)
    save(rgb, "aoi_shoe_basecolor.png")
    save_gray(rough, "aoi_shoe_roughness.png")
    save(height_to_normal(hgt, 0.6), "aoi_shoe_normal.png")
    save_gray(ao_from_height(hgt, 8), "aoi_shoe_ao.png")


def gen_metal(size=512):
    h = w = size
    n = fbm(h, w, octaves=4, base=8, persist=0.5, seed=61)
    # brushed: stretch noise along X
    small = np.random.default_rng(62).random((h, 8)).astype(np.float32)
    brushed = np.asarray(Image.fromarray((small * 255).astype(np.uint8))
                         .resize((w, h), Image.BICUBIC), np.float32) / 255.0
    hgt = brushed * 0.75 + n * 0.25
    base = hx("B9BCC9")[None, None, :] * np.ones((h, w, 1), np.float32)
    rgb = np.clip(base * (0.86 + 0.28 * hgt[..., None]), 0, 1)
    rough = np.clip(0.24 + (brushed - 0.5) * 0.22 + (n - 0.5) * 0.08, 0.10, 0.48)
    save(rgb, "aoi_metal_basecolor.png")
    save_gray(rough, "aoi_metal_roughness.png")
    save_gray(np.full((h, w), 1.0, np.float32), "aoi_metal_metallic.png")
    save(height_to_normal(hgt, 0.4), "aoi_metal_normal.png")


def gen_rubber(size=512):
    h = w = size
    n = fbm(h, w, octaves=5, base=48, persist=0.55, seed=71)
    hgt = n
    base = hx("15181F")[None, None, :] * np.ones((h, w, 1), np.float32)
    rgb = np.clip(base * (0.8 + 0.5 * n[..., None]), 0, 1)
    rough = np.clip(0.68 + (n - 0.5) * 0.18, 0.45, 0.92)
    save(rgb, "aoi_rubber_basecolor.png")
    save_gray(rough, "aoi_rubber_roughness.png")
    save(height_to_normal(hgt, 0.7), "aoi_rubber_normal.png")


def generate_all(outdir):
    global OUT
    OUT = outdir
    os.makedirs(outdir, exist_ok=True)
    gen_skin()
    gen_hair()
    gen_eye()
    gen_cloth()
    gen_shoe()
    gen_metal()
    gen_rubber()
    return sorted(os.listdir(outdir))


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else "/tmp/aoi_tex"
    files = generate_all(d)
    for f in files:
        print("  %-34s %8d bytes" % (f, os.path.getsize(os.path.join(d, f))))
    print("total textures:", len(files))
