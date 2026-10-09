# Wood floor planks

Oak, walnut, knotty pine, weathered grey decking or narrow white oak strips. Boards run across the tile in rows, and every row has its own joint offset, so butt joints stagger and the floor still repeats.

Each board is a slice of a log: the distance from a virtual pith axis, inclined slightly to the board, gives the growth rings, so flat-sawn boards show cathedral arches and boards cut near the pith show straight grain. Noise warps the rings, fine streaks add pores, and knots bend the rings around a dark core. `weathering` greys the wood, raises the hard late wood and opens checks near the board ends.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `wood_planks_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `wood_planks_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `wood_planks_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.12 to 1 |
| `height` | `wood_planks_height.png` | 1 | linear | white is high |
| `ao` | `wood_planks_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Oiled oak boards with fine cathedral grain.
- `walnut`: Dark lacquered walnut, wide boards, subtle rings.
- `knotty_pine`: Yellow pine with strong rings and frequent knots.
- `weathered_grey`: Sun-bleached grey deck boards with raised grain and checks.
- `white_oak_strip`: Narrow pale strips of lacquered white oak.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `board_rows` | int | 5 | 2 to 16 | Rows of boards across the tile height. |
| `boards_per_row` | int | 2 | 1 to 6 | Boards end to end in each row across the tile width. |
| `gap` | float | 0.004 | 0.0005 to 0.02 | Width of the joints between boards in texture units. |
| `ring_density` | float | 30 | 5 to 80 | Growth rings per texture unit of distance from the pith. |
| `ring_contrast` | float | 0.5 | 0 to 1 | Darkness of the late-wood bands. |
| `knots` | float | 0.2 | 0 to 1 | Chance of a knot on each board. |
| `board_variation` | float | 0.5 | 0 to 1 | Spread of tone between boards. |
| `gloss` | float | 0.5 | 0 to 1 | Finish from raw or weathered (0) to lacquered (1). |
| `weathering` | float | 0 | 0 to 1 | Raised grain, greying and end checks from exposure. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`wood_planks.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python wood_planks.py --size 1024 --seed 7 --preset walnut --out textures/wood_planks
python wood_planks.py --width 512 --height 256 --set board_rows=16 --orm --out maps
```

`--orm` also writes `wood_planks_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import wood_planks

maps = wood_planks.generate(512, 512, seed=3, preset="walnut")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.9 s (13.9 s to compute, 12 s to write the PNG files) with a peak of about 600 MB; 256 x 256 takes about 1.45 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/wood_planks/` of your project (for example `python wood_planks.py --size 1024 --out path/to/project/baltor/textures/wood_planks`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.008, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Grain comes from a geometric ring model with noise, not from wood anatomy; there is no ray fleck, figure or end grain. Boards run along the tile width only. Knots are simple ring distortions with a dark core. Occlusion is a blurred-height estimate.
