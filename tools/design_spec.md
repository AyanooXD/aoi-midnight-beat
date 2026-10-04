# Character Design Spec — ORIGINAL DESIGN

**Character name (original):** AOI MIZUKI
**Product name:** *AOI — Midnight Beat*
**Concept:** A stylish streetwear music-lover adult girl, ready for a game / VTuber pipeline.
**Origin:** 100% original design. No existing anime/game character, logo, or trademark is
reproduced or referenced.

---

## 1. Reference handling (honest note)

Two attachments were supplied:

| File | What it actually is |
|------|--------------------|
| `New Project.prisma` | A **Prisma Studio** archive. Unzipped it contains `project.proj` + one `.pobject`: a single `Cube` mesh with `Primitives.PrimitiveBox` and a `PMeshRenderer` using the default material. It carries **no character data at all**. |
| `file_…png` (1254×1254) | Character reference art. |

The PNG was extracted quantitatively (k-means palette, per-region luminance maps). Its image is
extremely dark overall (52% of pixels below #202631); readable art regions total only a few
percent of the frame. What **was** reliably extracted from it:

- A **cool charcoal / midnight-navy** dominant ground (`#0D1621`, `#1C202A`, `#2F2A35`)
- A **periwinkle / cornflower accent** — `#7C85F3`, the only saturated hue found (0.69% of frame)
- **Soft desaturated rose** skin tone — `#E1B2A8` / `#B38984`
- A warm **mid-grey** range `#8E8A97 … #ECE7E9`
- **Pure white** specular hits (`#ECE7E9`) — glossy hair / metal highlights

Those five facts drove the palette below. The face, hairstyle and garment *shapes* in that PNG were
not resolvable at any legible contrast, so every shape decision below is an original design choice,
made in that palette. This is stated plainly rather than claiming a match I could not verify.

---

## 2. Palette (final, used for materials + textures)

| Role | Hex | Notes |
|------|-----|-------|
| Skin base | `#F2C9BC` | soft rose, derived from reference `#E1B2A8`, lifted for a lit render |
| Skin shadow | `#D69C92` | |
| Blush | `#E8958F` | |
| Hair base | `#2E2A3A` | midnight charcoal-violet (reference `#2F2A35`) |
| Hair tip | `#8E86BE` | periwinkle gradient (reference `#7C85F3`) |
| Hair highlight | `#BFC8F5` | |
| Eye iris | `#6E7BF0` → `#3A44A8` | periwinkle iris, reference accent |
| Jacket / outer | `#262B3C` | (reference `#1C202A` lifted) |
| Jacket trim | `#7C85F3` | periwinkle accent stripe |
| Top inner | `#EDE9EE` | off-white |
| Skirt | `#1B2030` | deep midnight |
| Skirt pleat | `#2A3148` | |
| Denim / jeans | `#39405C` | |
| Socks | `#EDE9EE` | |
| Shoes upper | `#232838` | |
| Shoes sole | `#C9C6D2` | |
| Metal (headphones / buckles) | `#B9BCC9` | metallic |
| Rubber / earcup pad | `#15181F` | |
| Ribbon / accent | `#7C85F3` | |

## 3. Proportions

Stylized adult, **6.5 heads tall**, total height **1.63 m**, feet at `Z = 0`, facing **−Y**
(Blender front-view convention). Origin at the centre of the feet.

| Landmark | Z (m) |
|----------|-------|
| Crown | 1.630 |
| Eye line | 1.475 |
| Chin | 1.380 |
| Neck base | 1.310 |
| Shoulder (acromion) | 1.290 |
| Bust | 1.180 |
| Under-bust | 1.115 |
| Waist | 1.050 |
| Hip | 0.980 |
| Crotch | 0.880 |
| Elbow | 1.060 |
| Wrist | 0.840 |
| Knee | 0.500 |
| Ankle | 0.090 |
| Fingertip | 0.615 |

Head: 0.250 m tall, 0.168 m wide (W/H = 0.67), chin tapered, flat-ish face plane.
Deliberately **not** anatomically exaggerated — fashion-stylized only.

## 4. Face

Large anime eyes (0.048 × 0.050 m), low-set on the head (42% up from the chin), iris gradient +
two specular highlights, defined upper lash line, thin lower lash, subtle brows, minimal anime nose
wedge, small closed-lip smile. Symmetrical by construction (mirrored parameter space).

## 5. Hair

Midnight charcoal-violet base with a periwinkle gradient at the ends.
Scalp cap → straight fringe parted slightly off-centre (6 strands) → two cheek-length side
locks → long tapered back mass → **two high twin tails** bound with periwinkle ribbons.

## 6. Outfit (fully clothed, general-audience)

1. **Cropped bomber jacket** — midnight, open at the front, periwinkle ribbed collar/cuffs/hem,
   two front panels, sleeves following the arms, one chest patch pocket.
2. **Off-white inner top** — simple fitted tee.
3. **Pleated A-line mini skirt** — 12 pleats, midnight with lighter pleat faces.
4. **Socks** — off-white, mid-calf.
5. **Sneakers** — dark upper, light rubber sole + toe cap, laces.
6. **Over-ear headphones** — periwinkle/metal headband, dark earcups, cable.
7. **Hair ribbons** ×2, **choker** with small metal ring.

## 7. Object list

```
AOI_Body        AOI_Head        AOI_Eye_L        AOI_Eye_R      AOI_Eyebrows
AOI_Hair_Main   AOI_Hair_Bangs  AOI_Hair_Tail_L  AOI_Hair_Tail_R
AOI_Jacket      AOI_Jacket_Trim AOI_Top          AOI_Skirt      AOI_Socks
AOI_Shoes_L     AOI_Shoes_R     AOI_Headphones   AOI_Ribbon_L   AOI_Ribbon_R
AOI_Choker      AOI_Nose        AOI_Mouth
```

## 8. Materials (10)

`Skin`, `Eye`, `Hair`, `Cloth_Outer`, `Cloth_Trim`, `Cloth_Inner`, `Denim`, `Shoe`,
`Metal`, `Rubber`.

## 9. Texture plan (all generated procedurally in-repo, fully original)

| Map set | Resolution | Maps |
|---------|-----------|------|
| Skin | 1024 | BaseColor, Roughness, Normal, AO |
| Hair | 1024 | BaseColor, Roughness, Normal |
| Eye | 2048 | BaseColor (iris/sclera/highlights), Roughness, Normal |
| Cloth_Outer / Trim / Inner | 1024 | BaseColor, Roughness, Normal |
| Denim | 1024 | BaseColor, Roughness, Normal |
| Shoe | 1024 | BaseColor, Roughness, Normal |
| Metal | 512 | BaseColor, Roughness, Metallic |

Normal maps are generated from real height fields (Sobel gradient), not faked.
