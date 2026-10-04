AOI - MIDNIGHT BEAT
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
TEXTURES/  31 PBR maps (PNG, sRGB / linear as noted per map)
PREVIEWS/  8 rendered images
README.txt this file

TECHNICAL SPECIFICATION (measured from the shipped files)
--------------------------------------------------------
Height ................ 1.6384 m  (adult female, ~6.5 heads tall)
Width / depth ......... 0.4852 m x 0.2113 m
Orientation ........... Y-up in the OBJ file (height on +Y, standard OBJ
                         interchange). Imported Z-up it stands 1.6384 m tall
                         with feet at Z=0, facing -Y, origin at the centre of
                         the feet (Blender / Unity / Unreal convention)
Scale ................. 1 unit = 1 metre (no object has non-unit scale)

Vertices .............. 25546
UV coordinates ........ 35582
Normals ............... 22661
Faces ................. 26266
Triangles ............. 50748
Objects ............... 53 (named, logically separated)
Materials ............. 15
Textures .............. 31 PNG files
Textured materials .... 10 (skin, hair, eye, jacket, trim, inner cloth,
                         denim, shoe, metal, rubber)
Flat-colour accents ... 5 (brows, lashes, lips, eye socket, choker)

TEXTURE RESOLUTIONS (as actually produced)
-------------------------------------------
  2048 x 2048  (3 maps)  eye_basecolor.png, eye_normal.png, eye_roughness.png
  1024 x 1024  (21 maps)  cloth_inner_basecolor.png, cloth_inner_normal.png, cloth_inner_roughness.png, cloth_outer_basecolor.png, cloth_outer_normal.png, ...
  512 x 512  (7 maps)  metal_basecolor.png, metal_metallic.png, metal_normal.png, metal_roughness.png, rubber_basecolor.png, ...

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
