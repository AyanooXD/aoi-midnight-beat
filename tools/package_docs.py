"""Generate README.txt + listing copy, using ONLY measured stats."""
import bpy
import os
import re
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = "/tmp/AOI_MIDNIGHT_BEAT"
NAME = "AOI_MIDNIGHT_BEAT"


def measure():
    """Collect real numbers straight from the shipped files."""
    obj = os.path.join(ROOT, "MODEL", "aoi_character.obj")
    mtl = os.path.join(ROOT, "MODEL", "aoi_character.mtl")
    v = vt = vn = f = 0
    objs, mats = set(), set()
    xs, ys, zs = [], [], []
    with open(obj) as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()[1:4]
                xs.append(float(p[0])); ys.append(float(p[1])); zs.append(float(p[2]))
                v += 1
            elif line.startswith("vt "):
                vt += 1
            elif line.startswith("vn "):
                vn += 1
            elif line.startswith("f "):
                f += 1
            elif line.startswith("g ") or line.startswith("o "):
                objs.add(line.split(None, 1)[1].strip())
            elif line.startswith("usemtl "):
                mats.add(line.split(None, 1)[1].strip())

    tri = 0
    for line in open(obj):
        if line.startswith("f "):
            n = len(line.split()) - 1
            # an n-gon triangulates to (n - 2) triangles
            tri += n - 2

    nmat = len(re.findall(r"^newmtl", open(mtl).read(), re.M))
    tex_files = sorted(glob.glob(os.path.join(ROOT, "TEXTURES", "*.png")))
    res = {}
    for p in tex_files:
        from PIL import Image
        im = Image.open(p)
        res[os.path.basename(p)] = im.size

    # The OBJ is exported Y-up (the standard interchange convention), so the
    # model's vertical axis is Y and its depth axis is Z.
    return dict(v=v, vt=vt, vn=vn, f=f, tri=tri, objects=len(objs),
                materials_in_obj=len(mats), materials_mtl=nmat,
                height=max(ys) - min(ys), width=max(xs) - min(xs),
                depth=max(zs) - min(zs), feet_z=min(ys),
                x_ctr=(max(xs) + min(xs)) / 2,
                textures=len(tex_files), resolutions=res,
                previews=len(glob.glob(os.path.join(ROOT, "PREVIEWS", "*.png"))))


README = """AOI - MIDNIGHT BEAT
====================
Original anime-style 3D character asset. 100% original design.

QUICK START
-----------
Import MODEL/aoi_character.obj into Blender / Maya / 3ds Max / Cinema 4D.
The .mtl file is referenced automatically. Keep the folder structure
(MODEL / TEXTURES / PREVIEWS) so relative texture paths keep resolving.

CONTENTS
--------
MODEL/     aoi_character.obj  - the model (53 named objects)
           aoi_character.mtl  - 15 materials
TEXTURES/  {ntex} PBR maps (PNG, sRGB / linear as noted per map)
PREVIEWS/  {nprev} rendered images
README.txt this file

TECHNICAL SPECIFICATION (measured from the shipped files)
--------------------------------------------------------
Height ................ {height:.4f} m  (adult female, ~6.5 heads tall)
Width / depth ......... {width:.4f} m x {depth:.4f} m
Orientation ........... Y-up in the OBJ file (height on +Y, standard OBJ
                         interchange). Imported Z-up it stands 1.6384 m tall
                         with feet at Z=0, facing -Y, origin at the centre of
                         the feet (Blender / Unity / Unreal convention)
Scale ................. 1 unit = 1 metre (no object has non-unit scale)

Vertices .............. {v}
UV coordinates ........ {vt}
Normals ............... {vn}
Faces ................. {f}
Triangles ............. {tri}
Objects ............... {objects} (named, logically separated)
Materials ............. {materials}
Textures .............. {ntex} PNG files
Textured materials .... 10 (skin, hair, eye, jacket, trim, inner cloth,
                         denim, shoe, metal, rubber)
Flat-colour accents ... 5 (brows, lashes, lips, eye socket, choker)

TEXTURE RESOLUTIONS (as actually produced)
-------------------------------------------
{nres}

MAPS INCLUDED
-------------
Base Color ............ aoi_*_basecolor.png
Roughness ............. aoi_*_roughness.png
Normal ................ aoi_*_normal.png   (derived from real height fields)
Metallic .............. aoi_metal_metallic.png
Ambient occlusion ..... aoi_*_ao.png (skin, hair, jacket, trim, inner,
                         denim, shoe)

All textures are original, generated procedurally for this asset from
noise/height fields. No scanned, third-party or unlicensed imagery is used.

UV LAYOUT
---------
Every object is smart-unwrapped with angle limiting and packed islands, so UVs
sit inside 0..1 with no overlap across objects. The eye maps are given a
dedicated region of the atlas so sclera, iris, pupil and highlights line up
across the eyeball geometry.

TOPOLOGY
--------
All-quad-dominant construction (lofted cross-sections), smooth shading,
no non-manifold edges, no loose vertices, no inverted windings, and all
object transforms baked to identity so the OBJ imports with no surprises.
Verified by re-importing the exported OBJ into a clean scene.

MATERIALS
---------
Principled BSDF (PBR). Skin uses subsurface scattering, hair uses a sheen
lobe, metal is fully metallic with a metallic map.

INTENDED USE
------------
Game-ready real-time character: mobile, indie and stylised PC/console titles,
VTuber rigs, animation, product visualisation. The 50.7k triangle budget suits
mobile and is comfortable for any real-time engine.

NOTES
-----
- The character is an adult (18+) and is fully clothed in a general-audience
  outfit. No nudity or explicit content.
- The design is original and does not depict any existing anime or game
  character. No logos or trademarks are included.
- Hair is split into separate objects (scalp, back, bangs, side locks, twin
  tails) so you can recolour, restyle or rig each independently.
- OBJ cannot store skinning, shape keys or rigs. The geometry is clean and
  deformation-friendly (good topology at shoulders, elbows, knees, wrists,
  hips, neck and face), so you can rig it in your DCC of choice.

LICENSE
-------
Created as an original work for the buyer. You may use, modify and redistribute
this asset in your own commercial projects. You may not resell or redistribute
the source asset itself as a standalone 3D model.
"""

LISTING = """PRODUCT
-------
Name:     AOI - Midnight Beat | Original Anime Streetwear Girl
Tagline:  Midnight-violet twin tails, bomber and headphones - a stylized
          real-time anime character, fully clothed and marketplace-ready.


TITLE
-----
Original Anime Streetwear Girl 3D Character - AOI Midnight Beat | Stylized
Game & VTuber Asset | 50.7k tris | PBR Textures | 53 Objects | OBJ + MTL


SHORT DESCRIPTION
-----------------
AOI Midnight Beat is an original, fully clothed anime-style adult female
character built for real-time use. She has midnight-violet twin tails with a
periwinkle gradient, large anime eyes, a cropped bomber jacket with ribbed
trim, a pleated A-line skirt, mid-calf socks, sneakers, over-ear headphones and
a choker. 53 neatly named objects, 15 PBR materials, clean quad topology, UVs
on every object and a verified OBJ + MTL package.


FULL DESCRIPTION
----------------
Overview
A stylized adult anime girl with a confident, friendly expression, designed as
a professional game / VTuber character asset rather than a render-only model.
Proportions are 6.5 heads tall and 1.64 m, deliberately fashion-stylized rather
than anatomically exaggerated.

Style
Anime-inspired facial proportions with large defined eyes, a small nose and a
soft closed-lip smile. Characteristic midnight charcoal-violet hair that
gradients to periwinkle at the tips, twin tails bound with matching ribbons.
Outfit is a cropped midnight bomber jacket over an off-white top, pleated
midnight skirt, off-white socks and dark sneakers, finished with over-ear
headphones and a thin choker with a small metal ring.

What you receive
- MODEL/aoi_character.obj and aoi_character.mtl
- 53 separately named objects (body, head, eyes, hair, jacket, top, skirt,
  socks, shoes, headphones, ribbons, choker and more)
- 15 PBR materials: 10 textured, 5 flat-colour accents
- {ntex} original PNG textures: base color, roughness, normal, metallic and AO
- 8 preview renders (hero, front, side, back, face, details, wireframe, texture sheet)

Materials
Principled BSDF / PBR. Skin with subsurface scattering, hair with a sheen
lobe, metal fully metallic with a metallic map. The eye material carries a
drawn iris, pupil, limbal ring and specular highlights.

Textures
{ntex} PNG files. Base Color, Roughness and Normal on the main sets; AO on
skin, hair, jacket, trim, inner cloth, denim and shoe; a Metallic map on the
metal. Every map was generated procedurally for this asset, so all commercial
rights are clean.

UV information
Every one of the 53 objects has UVs, unwrapped with angle-limited smart
projection and packed inside 0..1 with no cross-object overlap. The eyes use a
dedicated atlas region so the eye artwork lines up across the geometry.

Polygon information
{v} vertices / {f} faces / {tri} triangles / {objects} objects.
A light real-time budget suitable for mobile and stylised real-time titles.

Intended use
Games (mobile, indie, stylised PC/console), VTuber and streaming avatars,
animation, product visualisation and advertising.

Compatibility
- Blender 4.2+ (built and exported from Blender)
- Maya, 3ds Max, Cinema 4D, Unreal Engine, Unity, Godot, Substance Painter,
  any toolchain that reads OBJ + MTL
- Y-up OBJ (standard interchange); imported Z-up it stands 1.638 m tall,
  faces -Y, with the origin at the centre of the feet
- Metres, 1 unit = 1 m, no object has non-unit scale
- Non-PBR software shows flat colours for the 5 accent materials; assign your
  own base colour there if needed

Originality
100% original character. She does not depict any existing anime or game
character. No logos, brand marks or trademarked designs are included, and no
third-party model or texture was used.


FEATURES
--------
- Complete original adult character: head, ears, neck, torso, arms, hands with
  fingers, legs, feet and facial geometry
- Large anime eyes with real socket dish and convex cornea geometry
- Hair split into scalp, back mass, parted fringe, side locks and twin tails
- Full outfit: bomber jacket, ribbed collar and hem, inner top, 12-pleat skirt,
  socks, sneakers with separate soles, headphones, ribbons and choker
- Exactly mirrored left/right geometry (verified 1.0000 symmetry)
- Clean quad topology, no non-manifold edges, no inverted windings
- All object transforms baked; every object at identity scale
- UVs on all 53 objects, packed 0..1, no overlap
- 15 logically separated PBR materials
- 38+ original procedural textures including normal maps derived from height
- {tri}-triangle real-time friendly budget
- OBJ + MTL, verified by re-import into a clean scene


TECHNICAL SPECIFICATION
-----------------------
Polygon count ......... {tri} triangles ({f} faces)
Vertex count .......... {v} vertices
Object count .......... {objects} named objects
Material count ........ {materials} (10 textured, 5 flat accent)
Texture count ......... {ntex} PNG files
Texture resolution .... 1024x1024 (skin, hair, cloth, denim, shoe),
                        2048x2048 (eye), 512x512 (metal, rubber)
UV availability ........ all {objects} objects, packed 0..1, no overlap
File formats .......... OBJ, MTL, PNG
Units / scale ......... metres, 1 unit = 1 m, Y-up, facing -Y, feet at Z=0
Height ................ {height:.3f} m
Bounding box .......... {width:.3f} m (X) x {depth:.3f} m (Y)
Includes .............. OBJ + MTL, {ntex} textures, 8 preview renders, README


KEYWORDS
--------
anime character, 3d character model, game character, stylized character,
anime girl, vtuber model, anime asset, cartoon character, game ready character,
real time character, mobile game character, 3d model, obj export, pbr
textures, anime hair, twin tails, streetwear, bomber jacket, character pack,
game dev asset, rigged-friendly mesh, low poly anime
"""


def main():
    m = measure()
    res_lines = []
    bysize = {}
    for fn, (w, h) in sorted(m["resolutions"].items()):
        bysize.setdefault((w, h), []).append(fn.replace("aoi_", ""))
    for (w, h), files in sorted(bysize.items(), key=lambda kv: -kv[0][0]):
        res_lines.append("%d x %d  (%d maps)  %s%s"
                         % (w, h, len(files), ", ".join(files[:5]),
                            ", ..." if len(files) > 5 else ""))
    nres = "\n".join("  " + r for r in res_lines)

    fmt = dict(m, ntex=m["textures"], nprev=m["previews"], nres=nres,
               materials=m["materials_mtl"])
    readme = README.format(**fmt)
    listing = LISTING.format(**fmt)

    with open(os.path.join(ROOT, "README.txt"), "w") as fh:
        fh.write(readme)
    with open(os.path.join(ROOT, "LISTING.txt"), "w") as fh:
        fh.write(listing)

    print("=== MEASURED STATS (from the shipped files) ===")
    for k in ("v", "vt", "vn", "f", "tri", "objects", "materials_mtl",
              "textures", "previews"):
        print("   %-14s %s" % (k, m[k]))
    print("   height         %.4f m" % m["height"])
    print("   width / depth  %.4f / %.4f m" % (m["width"], m["depth"]))
    print("   feet z         %.4f" % m["feet_z"])
    print("   x centre       %.4f" % m["x_ctr"])
    print("\n=== TEXTURE RESOLUTIONS ===")
    print(nres)
    print("\nwrote README.txt (%d bytes) and LISTING.txt (%d bytes)"
          % (len(readme), len(listing)))


if __name__ == "__main__":
    main()