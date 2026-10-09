# Tartan woven from a thread-count sett in 2/2 twill

A highland check of navy and green crossed by red with a yellow overcheck, a black, grey and white dress sett, a fuzzy brown and rust autumn plaid, a two-colour buffalo check or bright cotton madras. A sett is a half sequence of colours and thread counts reflected at both ends, the first and last colours being the pivots; the same sequence sets the warp, whose colours change across the width, and the weft, whose colours change down the height, and the tile holds a whole number of repeats.

The capability beyond woven_cloth's uniform-colour drafts is the sett colour system and its crossings: a 2/2 twill puts the warp on top at two crossings in four, shifting by one every row, so where warp and weft colours differ the squares show the finely hatched blend typical of tartan, and where they match they are solid. Threads have round profiles, dip where they pass under, vary slightly in colour, and wool fuzz softens colour and relief.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `tartan_sett_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.92 |
| `normal` | `tartan_sett_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `tartan_sett_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.55 to 1 |
| `height` | `tartan_sett_height.png` | 1 | linear | white is high |
| `ao` | `tartan_sett_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Highland check: navy and green grounds crossed by red with a yellow overcheck.
- `grey_dress`: Dress sett in white, grey and black with a fine charcoal line.
- `autumn_plaid`: Brown, rust and cream plaid with a narrow orange stripe, soft and fuzzy.
- `buffalo_check`: Two-colour red and black block check, two repeats across.
- `madras_bright`: Bright cotton madras: pink, lime, yellow and sky blue, crisp and smooth.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `repeats` | int | 1 | 1 to 4 | Whole sett repeats across the tile. |
| `thread_scale` | int | 1 | 1 to 3 | Multiplies every thread count; larger values show finer threads in the same stripes. |
| `relief` | float | 0.6 | 0 to 1 | Height of the yarn and the twill ridges. |
| `fuzz` | float | 0.5 | 0 to 1 | Wool fuzz blurring colours and relief. |
| `yarn_variation` | float | 0.35 | 0 to 1 | Colour variation from thread to thread. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`tartan_sett.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python tartan_sett.py --size 1024 --seed 7 --preset grey_dress --out textures/tartan_sett
python tartan_sett.py --width 512 --height 256 --set repeats=4 --orm --out maps
```

`--orm` also writes `tartan_sett_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import tartan_sett

maps = tartan_sett.generate(512, 512, seed=3, preset="grey_dress")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 19.4 s (9.9 s to compute, 9.5 s to write the PNG files) with a peak of about 560 MB; 256 x 256 takes about 1.22 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/tartan_sett/` of your project (for example `python tartan_sett.py --size 1024 --out path/to/project/baltor/textures/tartan_sett`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The setts are invented and do not reproduce registered tartans. Thread counts are kept low so a thread spans several pixels at 256 x 256, which makes the cloth look coarser than real tartan; raise `thread_scale` and the output size for finer cloth. Threads are idealized round yarns on a regular grid without crimp variation or weaving faults, and a sett whose repeat is not a multiple of four gets its first pivot widened to keep the twill seamless. Fuzz is noise and a blur. Occlusion is a blurred-height estimate.
