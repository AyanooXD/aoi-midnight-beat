"""Diagnose 'textures/colors are not showing' against the shipped package.

Checks, in order of how often each turns out to be the real cause:
  1. are the texture FILES valid images with the right dimensions?
  2. does every MTL map reference resolve, and is the path relative-correct?
  3. do the textures contain real colour variation, or are they flat/near-black?
  4. does the OBJ actually carry UVs?
  5. do the materials' base colours differ enough to see at a glance?
"""
import os
import re
import sys
import glob
import numpy as np
from PIL import Image

ROOT = "/home/user/project/ANIME_CHARACTER_NAME"
MODEL = os.path.join(ROOT, "MODEL")
OBJ = os.path.join(MODEL, "aoi_character.obj")
MTL = os.path.join(MODEL, "aoi_character.mtl")
TEX = os.path.join(ROOT, "TEXTURES")


def hdr(t):
    print("\n" + "=" * 68)
    print(t)
    print("=" * 68)


def check_files():
    hdr("1. TEXTURE FILES - valid images? right size? real content?")
    bad = []
    flat = []
    notes = []
    rows = []
    for p in sorted(glob.glob(os.path.join(TEX, "*.png"))):
        fn = os.path.basename(p)
        try:
            im = Image.open(p)
            im.load()
            a = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
        except Exception as e:
            bad.append("%s: unreadable (%s)" % (fn, e))
            continue
        lum = a @ np.array([0.299, 0.587, 0.114])
        std = float(lum.std())
        mean = float(lum.mean())
        flag = ""
        is_n = "normal" in fn
        if is_n:
            # Normal maps are centred on the flat-surface value 0.5 (=128 in 8-bit)
            # and naturally have a low std. Only flag a genuinely uniform map
            # or one that is not centred on the flat-normal value.
            centred = abs(mean - 0.5)
            if std < 0.002 and centred < 0.01:
                flag = " (intentionally flat)"
            elif std < 0.008:
                flag = " ** WEAK VARIATION **"
            elif centred > 0.06:
                flag = " ** OFF-CENTRE (not a flat-surface normal) **"
        elif "metallic" in fn:
            # a constant metallic value is correct for a single-value metal
            if std < 0.005:
                flag = " (intentionally uniform)"
            else:
                flag = " (varying metallic)"
        else:
            if std < 0.004:
                flag = " ** FLAT **"
            if mean < 0.02:
                flag = " ** NEAR-BLACK **"
        if flag.startswith('**'):
            flat.append("""%s: %s""" % (fn, flag.strip('* ')))
        elif flag:
            notes.append("%s: %s" % (fn, flag.strip()))
        rows.append((fn, im.size, mean, std, flag))
    for fn, size, mean, std, flag in rows:
        print("  %-34s %-10s mean %.3f  std %.3f%s"
              % (fn, "%dx%d" % size, mean, std, flag))
    print("\n  files: %d   unreadable: %d   defective: %d   intentional: %d"
          % (len(rows), len(bad), len(flat), len(notes)))
    for nn in notes:
        print("      . %s" % nn)
    for b in bad:
        print("   !! %s" % b)
    for f in flat:
        print("   !! %s" % f)
    return not bad and not flat


def check_mtl():
    hdr("2. MTL -> texture path resolution")
    txt = open(MTL).read()
    maps = re.findall(r"^(map_\w+)\s+(\S+)", txt, re.M)
    print("  map_ references found: %d" % len(maps))
    ok = bad = 0
    for key, val in maps:
        p = os.path.normpath(os.path.join(MODEL, val))
        exists = os.path.exists(p)
        alt = os.path.join(TEX, os.path.basename(val))
        if exists:
            ok += 1
        else:
            bad += 1
            print("   !! %s %s -> NOT FOUND (also tried %s: %s)"
                  % (key, val, alt, os.path.exists(alt)))
    print("  resolve from MODEL/: %d ok, %d broken" % (ok, bad))
    # do the referenced files actually live in TEXTURES/?
    print("\n  first 3 references as written in the MTL:")
    for key, val in maps[:3]:
        print("    %-8s %s" % (key, val))
    return bad == 0


def check_uvs():
    hdr("3. OBJ UV COVERAGE")
    v = vt = f = 0
    uv_sum = 0
    us, vs = [], []
    cur_uv = None
    obj_uv = {}
    for line in open(OBJ):
        if line.startswith("vt "):
            p = line.split()[1:3]
            us.append(float(p[0])); vs.append(float(p[1]))
            vt += 1
        elif line.startswith("v "):
            v += 1
        elif line.startswith("f "):
            f += 1
            if uv_sum < 1:
                # check that faces reference a real vt index
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    if len(parts) > 1 and parts[1]:
                        uv_sum += 1
                        break
    print("  v=%d  vt=%d  f=%d" % (v, vt, f))
    if us:
        print("  U range %.4f .. %.4f" % (min(us), max(us)))
        print("  V range %.4f .. %.4f" % (min(vs), max(vs)))
        inside = sum(1 for u in us if -0.001 <= u <= 1.001)
        print("  UVs inside 0..1: %d/%d (%.1f%%)"
              % (inside, len(us), 100.0 * inside / len(us)))
    print("  faces referencing a texture index: %s"
          % ("yes" if uv_sum else "NO - this is the bug"))
    return bool(uv_sum) and vt > 0


def check_material_spread():
    hdr("4. MATERIAL COLOUR SPREAD (would you see colour differences?)")
    txt = open(MTL).read()
    cur = None
    info = {}
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("newmtl"):
            cur = s.split(None, 1)[1]
            info[cur] = {"Kd": None, "map": None}
        elif cur and s.startswith("Kd "):
            info[cur]["Kd"] = [float(x) for x in s.split()[1:4]]
        elif cur and s.startswith("map_Kd"):
            info[cur]["map"] = s.split(None, 1)[1].strip()
    textured, flats = 0, 0
    for name, d in info.items():
        if d["map"]:
            textured += 1
            print("  %-14s TEXTURED  map_Kd=%-28s (Kd %s)"
                  % (name, os.path.basename(d["map"]), d["Kd"]))
        else:
            flats += 1
            print("  %-14s FLAT      Kd=%s" % (name, d["Kd"]))
    print("\n  textured: %d   flat: %d" % (textured, flats))
    return textured > 0 and flats > 0


def main():
    a = check_files()
    b = check_mtl()
    c = check_uvs()
    d = check_material_spread()
    hdr("VERDICT")
    print("  texture files valid ....... %s" % ("PASS" if a else "FAIL"))
    print("  MTL paths resolve ......... %s" % ("PASS" if b else "FAIL"))
    print("  UVs present ............... %s" % ("PASS" if c else "FAIL"))
    print("  material colour spread ... %s" % ("PASS" if d else "FAIL"))
    print()
    print("  If all four PASS, the package is sound and the problem is in HOW")
    print("  you are viewing it (viewport mode, MTL not loaded, UV panel).")


if __name__ == "__main__":
    main()