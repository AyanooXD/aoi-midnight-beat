"""Final validation checklist - every claim verified against the shipped package."""
import bpy
import os
import re
import sys
import glob
from PIL import Image

ROOT = "/tmp/AOI_MIDNIGHT_BEAT"


def check():
    rows = []
    obj = os.path.join(ROOT, "MODEL", "aoi_character.obj")
    mtl = os.path.join(ROOT, "MODEL", "aoi_character.mtl")

    obj_txt = open(obj).read()
    mtl_txt = open(mtl).read()

    # --- structure ---
    for d in ("MODEL", "TEXTURES", "PREVIEWS"):
        p = os.path.join(ROOT, d)
        rows.append(("package contains /%s/" % d, os.path.isdir(p),
                     "%d files" % len(os.listdir(p)) if os.path.isdir(p) else "MISSING"))
    rows.append(("character.obj present", os.path.exists(obj),
                 "%d bytes" % os.path.getsize(obj) if os.path.exists(obj) else "-"))
    rows.append(("character.mtl present", os.path.exists(mtl),
                 "%d bytes" % os.path.getsize(mtl) if os.path.exists(mtl) else "-"))
    rows.append(("README.txt present", os.path.exists(os.path.join(ROOT, "README.txt")),
                 "%d bytes" % os.path.getsize(os.path.join(ROOT, "README.txt"))))
    rows.append(("LISTING.txt present", os.path.exists(os.path.join(ROOT, "LISTING.txt")),
                 "%d bytes" % os.path.getsize(os.path.join(ROOT, "LISTING.txt"))))

    # --- previews ---
    want = ["hero.png", "front.png", "side.png", "back.png", "face.png",
            "details.png", "wireframe.png", "textures.png"]
    for w in want:
        p = os.path.join(ROOT, "PREVIEWS", w)
        ok = os.path.exists(p)
        sz = Image.open(p).size if ok else (0, 0)
        rows.append(("preview %s" % w, ok and os.path.getsize(p) > 20000,
                     "%dx%d" % sz))

    # --- textures linked ---
    texs = sorted(glob.glob(os.path.join(ROOT, "TEXTURES", "*.png")))
    maps = re.findall(r"^map_\w+\s+(\S+)", mtl_txt, re.M)
    resolved = [m for m in maps
                if os.path.exists(os.path.join(ROOT, "TEXTURES", os.path.basename(m)))]
    rows.append(("all MTL map refs resolve", len(maps) > 0 and len(resolved) == len(maps),
                 "%d/%d resolve" % (len(resolved), len(maps))))
    rows.append(("textures shipped in /TEXTURES/", len(texs) > 0, "%d PNG" % len(texs)))
    strays = glob.glob(os.path.join(ROOT, "MODEL", "*.png"))
    rows.append(("no stray png in /MODEL/", len(strays) == 0, "%d stray" % len(strays)))

    # --- materials & geometry ---
    nmat = len(re.findall(r"^newmtl", mtl_txt, re.M))
    rows.append(("materials present (MTL)", nmat > 0, "%d materials" % nmat))
    usemtl = set(re.findall(r"^usemtl (\S+)", obj_txt, re.M))
    newmtl = set(re.findall(r"^newmtl (\S+)", mtl_txt, re.M))
    rows.append(("every usemtl defined in MTL", usemtl <= newmtl,
                 "%d/%d" % (len(usemtl & newmtl), len(usemtl))))
    v = len(re.findall(r"^v ", obj_txt, re.M))
    vt = len(re.findall(r"^vt ", obj_txt, re.M))
    f = len(re.findall(r"^f ", obj_txt, re.M))
    rows.append(("has vertices", v > 0, "%d" % v))
    rows.append(("has UV coordinates", vt > 0, "%d" % vt))
    rows.append(("has faces", f > 0, "%d" % f))
    objs = set(re.findall(r"^o (\S+)", obj_txt, re.M))
    rows.append(("named objects", len(objs) > 10, "%d objects" % len(objs)))
    rows.append(("object names are AOI_*", all(n.startswith("AOI_") for n in objs),
                 "all prefixed" if all(n.startswith("AOI_") for n in objs) else "some differ"))

    # --- triangles (n-gon aware) ---
    tri = 0
    for line in obj_txt.splitlines():
        if line.startswith("f "):
            tri += len(line.split()) - 1 - 2
    rows.append(("triangle count in real-time range", 20000 < tri < 120000,
                 "%d tris" % tri))

    # --- adult / modest outfit ---
    names = " ".join(objs).lower()
    rows.append(("fully clothed (garments present)",
                 all(k in names for k in ("jacket", "top", "skirt", "sock", "shoe")),
                 "jacket+top+skirt+sock+shoe"))
    rows.append(("no nude/body-only variant shipped",
                 not any(k in names for k in ("nude", "naked", "nsfw")),
                 "none found"))

    # --- originality ---
    banned = ["pokemon", "naruto", "ghibli", "anime girl 01", "mikoto",
              "rem", "asuna", "hatsune", "genshin", "miku", "remilia"]
    hit = [b for b in banned if b in obj_txt.lower() or b in mtl_txt.lower()]
    rows.append(("no third-party character names/logos", not hit, "none" if not hit else str(hit)))
    rows.append(("no image files other than our generated textures",
                 all(t.startswith("aoi_") for t in os.listdir(os.path.join(ROOT, "TEXTURES"))),
                 "all aoi_*"))

    # --- temp files ---
    temp = [f for f in os.listdir(ROOT)
            if f.endswith((".blend", ".blend1", ".py", ".tmp", ".bak", "__pycache__"))]
    rows.append(("no temporary files in package", not temp, str(temp) if temp else "clean"))

    print("=" * 74)
    print("FINAL VALIDATION - %s" % ROOT)
    print("=" * 74)
    npass = 0
    for label, ok, detail in rows:
        mark = "PASS" if ok else "FAIL"
        npass += bool(ok)
        print("  [%s] %-42s %s" % (mark, label, detail))
    print("-" * 74)
    print("  %d/%d checks passed" % (npass, len(rows)))
    return npass == len(rows)


if __name__ == "__main__":
    sys.exit(0 if check() else 1)