# Interlocking concrete pavers: zigzag, dogbone, wavy

Grey zigzag pavers, red dogbone pavers, charcoal wavy pavers or a tumbled brown, tan and charcoal blend. Pavers two units long and one unit wide lie in rows that alternate their offset, `pavers_per_row` across the tile and twice as many rows down it, so the pattern repeats in both directions.

The joint between two rows follows one periodic curve that both rows read, so neighbours interlock exactly: a cosine with the paver length as period makes dogbone pavers wide at their ends and narrow in the middle, while a zigzag or sine with half that period makes parallel zigzag or wavy pavers. `amplitude` sets how far the sides swing. The distance to the sides and ends shapes the `chamfer` above jointing sand at `joint_fill`; `aggregate` speckles the face with stone and `tumbling` rounds and chips the edges.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `interlocking_pavers_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `interlocking_pavers_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `interlocking_pavers_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.45 to 1 |
| `height` | `interlocking_pavers_height.png` | 1 | linear | white is high |
| `ao` | `interlocking_pavers_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey concrete zigzag pavers with light sand joints.
- `red_dogbone`: Red concrete I-shaped dogbone pavers interlocking in stretcher bond.
- `charcoal_wavy`: Charcoal wavy pavers with fine aggregate and tight joints.
- `tumbled_blend`: Tumbled dogbone pavers in a brown, tan and charcoal blend.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `shape` | int | 0 | 0 to 2 | 0 zigzag sides (two teeth per paver), 1 dogbone or I shape (wide ends, narrow middle), 2 wavy sides (a sine with two waves per paver). |
| `pavers_per_row` | int | 4 | 2 to 10 | Pavers across the tile in each row; the tile holds twice as many rows. |
| `amplitude` | float | 0.16 | 0.04 to 0.3 | How far the curved sides swing, in paver widths. |
| `joint_width` | float | 0.05 | 0.015 to 0.15 | Sand joint width in paver widths. |
| `chamfer` | float | 0.06 | 0.01 to 0.2 | Width of the bevelled top edge in paver widths. |
| `joint_fill` | float | 0.6 | 0 to 0.95 | Height of the jointing sand relative to the paver tops. |
| `aggregate` | float | 0.4 | 0 to 1 | Exposed stone aggregate speckling the concrete face. |
| `tumbling` | float | 0 | 0 to 1 | Tumbled, rounded and chipped edges of antique-style pavers. |
| `colour_variation` | float | 0.35 | 0 to 1 | Spread of colour between pavers. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`interlocking_pavers.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python interlocking_pavers.py --size 1024 --seed 7 --preset red_dogbone --out textures/interlocking_pavers
python interlocking_pavers.py --width 512 --height 256 --set shape=2 --orm --out maps
```

`--orm` also writes `interlocking_pavers_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import interlocking_pavers

maps = interlocking_pavers.generate(512, 512, seed=3, preset="red_dogbone")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 28.4 s (19.3 s to compute, 9.1 s to write the PNG files) with a peak of about 601 MB; 256 x 256 takes about 1.99 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/interlocking_pavers/` of your project (for example `python interlocking_pavers.py --size 1024 --out path/to/project/baltor/textures/interlocking_pavers`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.015, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Pavers are laid in stretcher bond only; herringbone and basket layouts of interlocking shapes are out of scope. Paver ends are straight and the curved sides follow one periodic curve, a simplification of real paver catalogues. Aggregate, stains and chips are noise approximations. Occlusion is a blurred-height estimate, not ray traced.
