# AOI — Midnight Beat

Original anime-style 3D character asset, built from scratch with Blender's
Python API and exported as a clean OBJ + MTL package.

**Character:** AOI Mizuki — a stylized adult (18+), 6.5-heads-tall, 1.64 m,
fully clothed anime woman. Midnight charcoal-violet hair graduating to a
periwinkle gradient, twin tails with ribbon ties, large anime eyes, cropped
bomber jacket, pleated A-line skirt, mid-calf socks, sneakers, over-ear
headphones and a choker.

## The deliverable

```
ANIME_CHARACTER_NAME/
├── MODEL/
│   ├── aoi_character.obj     53 named objects, 25,546 verts, 50,748 tris
│   └── aoi_character.mtl     15 PBR materials
├── TEXTURES/                 31 original PNG maps
├── PREVIEWS/                 8 renders (hero/front/side/back/face/details/wireframe/textures)
├── README.txt                full technical spec
└── LISTING.txt               marketplace listing copy
```

See [`ANIME_CHARACTER_NAME/README.txt`](ANIME_CHARACTER_NAME/README.txt) for
import instructions and the full specification.

## Quick start

```bash
# In Blender: File > Import > Wavefront (.obj) > MODEL/aoi_character.obj
# Keep the MODEL/ and TEXTURES/ folders in place so relative paths resolve.
```

## Verification

Everything below is measured, not asserted:

| Check | Result |
|---|---|
| Pre-export QC | PASS — 0 non-manifold edges, 0 inverted windings, 0 loose verts |
| Left/right symmetry | 1.0000 on all 10 mirrored features |
| UVs | present on all 53 objects, packed inside 0..1, no overlap |
| Materials | 15 defined, every `usemtl` resolves, 0 broken texture paths |
| OBJ round-trip | PASS — re-imported into a clean scene, geometry/UV/materials intact |
| Package validation | 31/31 checks |

## How it was built

The whole asset is generated procedurally — no external model, scan, or
texture was used.

```
tools/
├── aoi_lib.py        mesh helpers: lofted cross-sections, sheets, solidify, exact mirroring
├── build_body.py     head, ears, neck, torso, arms, hands+fingers, legs, feet
├── build_face.py     eyes (socket + cornea), lashes, brows, nose, lips
├── build_hair.py     scalp shell, back mass, parted fringe, side locks, twin tails
├── build_cloth.py    bomber jacket, top, pleated skirt, socks, sneakers, headphones, ribbons, choker
├── textures.py       procedural PBR maps (value-noise fBm, Sobel normals)
├── assemble.py       geometry + materials + UV layout
├── studio.py         studio lighting rig and camera placement
├── export_obj.py     OBJ/MTL export + re-import verification
├── package_docs.py   README / listing generated from measured stats
└── final_check.py    31-point package validation
```

Reproduce the asset:

```bash
pip install bpy numpy pillow scipy
python3 tools/make_asset.py     # build + save the .blend
python3 tools/qc.py             # geometry / UV / material QC
python3 tools/export_obj.py     # OBJ+MTL export and round-trip check
python3 tools/final_check.py    # package validation
```

## Originality & licensing

100% original character and design. She does not depict any existing anime or
game character. No logos, brand marks, or trademarked designs are included. All
textures are generated procedurally for this asset, so commercial rights are
clean.

You may use, modify and redistribute this asset in your own commercial
projects. You may not resell or redistribute the source asset itself as a
standalone 3D model.