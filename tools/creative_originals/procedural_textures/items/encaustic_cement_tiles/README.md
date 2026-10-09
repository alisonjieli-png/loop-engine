# Encaustic cement tiles with symmetric inlay motifs

Black and terracotta stars on cream with ochre corner circles, blue florals on white, black and white nested geometry, or worn green and rose rosettes inside a border frame. `tiles_across` tiles cross the tile with thin joints, so the floor repeats in both directions.

Every point of a tile is folded into one octant of the square by mirroring, so a motif drawn once in the octant takes the eightfold symmetry of the square, and the quarter and half circles at its edges join into whole circles with the neighbouring tiles. A motif is a short list of shapes drawn in order and coloured with up to three inlay colours on the background; `family` picks the kind of design and `motif_variant` its proportions. Inlay boundaries are softened over `edge_softness` pixels, `wear` fades and scuffs the face and chips the tile edges, and `pores` adds small air holes.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `encaustic_cement_tiles_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `encaustic_cement_tiles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `encaustic_cement_tiles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.4 to 1 |
| `height` | `encaustic_cement_tiles_height.png` | 1 | linear | white is high |
| `ao` | `encaustic_cement_tiles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Eight-point stars in black and terracotta on cream with ochre corner circles.
- `blue_floral`: White tiles with cobalt and sky blue petals around a small centre.
- `geometric_mono`: Black, white and grey nested squares and diamonds, four tiles per side.
- `rosette_border`: Faded green, rose and sand rosettes framed by a border band, well worn.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `tiles_across` | int | 2 | 1 to 8 | Tiles across the tile width (and height). |
| `family` | int | 0 | 0 to 3 | Motif family: 0 eight-point star with corner circles, 1 floral with axis and diagonal petals, 2 geometric nested squares and diamonds, 3 rosette inside a border frame. |
| `motif_variant` | int | 0 | 0 to 99 | Which design of the family: sizes and proportions of its shapes. |
| `joint_width` | float | 0.006 | 0 to 0.03 | Joint between tiles in tile widths. |
| `edge_softness` | float | 1.5 | 0.5 to 4 | Width in pixels over which inlay colours blend at their boundaries. |
| `wear` | float | 0.3 | 0 to 1 | Faded, scuffed patches and slightly chipped tile edges. |
| `pores` | float | 0.4 | 0 to 1 | Small pores and air holes in the cement face. |
| `colour_variation` | float | 0.3 | 0 to 1 | Spread of tone between tiles. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`encaustic_cement_tiles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python encaustic_cement_tiles.py --size 1024 --seed 7 --preset blue_floral --out textures/encaustic_cement_tiles
python encaustic_cement_tiles.py --width 512 --height 256 --set tiles_across=8 --orm --out maps
```

`--orm` also writes `encaustic_cement_tiles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import encaustic_cement_tiles

maps = encaustic_cement_tiles.generate(512, 512, seed=3, preset="blue_floral")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.6 s (17.2 s to compute, 8.3 s to write the PNG files) with a peak of about 641 MB; 256 x 256 takes about 1.97 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/encaustic_cement_tiles/` of your project (for example `python encaustic_cement_tiles.py --size 1024 --out path/to/project/baltor/textures/encaustic_cement_tiles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.006, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Motifs come from four families of simple shapes (stars, discs, rings, petals, squares, diamonds, frames) varied by motif_variant; free-form floral drawing and real catalogue patterns are out of scope. Every tile carries the same motif, so layouts that rotate or alternate tiles are not produced. Inlay colours are flat with softened boundaries; wear and pores are noise approximations. Occlusion is a blurred-height estimate, not ray traced.
