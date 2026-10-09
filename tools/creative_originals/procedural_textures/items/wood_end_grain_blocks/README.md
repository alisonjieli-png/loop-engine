# End-grain wood blocks

Maple, walnut, mixed hardwood or rough pine log ends. The tile is a grid of square blocks; every other row can shift by `stagger`. Each block is the cross-section of a small log: rings circle a pith point that may lie inside the block or beyond its edge, where only arcs show.

Medullary rays are thin radial streaks, a few radial checks crack outward from the pith, and dark glue lines separate the blocks. The mixed preset picks a species per block.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `wood_end_grain_blocks_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.88 |
| `normal` | `wood_end_grain_blocks_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `wood_end_grain_blocks_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.2 to 1 |
| `height` | `wood_end_grain_blocks_height.png` | 1 | linear | white is high |
| `ao` | `wood_end_grain_blocks_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Oiled maple end grain in a straight grid.
- `walnut_staggered`: Dark walnut blocks with staggered rows and subtle rings.
- `mixed_hardwood`: Maple, cherry and walnut blocks mixed, oiled.
- `rough_pine`: Weathered pine log ends with wide rings and deep checks.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `blocks_across` | int | 4 | 1 to 12 | Blocks across the tile (rows down the tile match, so blocks stay square). |
| `stagger` | float | 0 | 0 to 0.5 | Offset of every other row in block widths (alternation repeats cleanly with an even block count). |
| `ring_density` | float | 45 | 10 to 120 | Growth rings per texture unit of radius. |
| `ring_contrast` | float | 0.6 | 0 to 1 | Darkness of the late-wood rings. |
| `rays` | float | 0.4 | 0 to 1 | Visibility of the radial medullary rays. |
| `checks` | float | 0.3 | 0 to 1 | Radial drying cracks from the pith. |
| `glue_line` | float | 0.003 | 0.0005 to 0.012 | Width of the glue joints in texture units. |
| `block_variation` | float | 0.6 | 0 to 1 | Spread of tone between blocks. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`wood_end_grain_blocks.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python wood_end_grain_blocks.py --size 1024 --seed 7 --preset walnut_staggered --out textures/wood_end_grain_blocks
python wood_end_grain_blocks.py --width 512 --height 256 --set blocks_across=12 --orm --out maps
```

`--orm` also writes `wood_end_grain_blocks_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import wood_end_grain_blocks

maps = wood_end_grain_blocks.generate(512, 512, seed=3, preset="walnut_staggered")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 26 s (13.4 s to compute, 12.6 s to write the PNG files) with a peak of about 559 MB; 256 x 256 takes about 1.73 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/wood_end_grain_blocks/` of your project (for example `python wood_end_grain_blocks.py --size 1024 --out path/to/project/baltor/textures/wood_end_grain_blocks`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.005, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Rings are circles around one pith per block with noise, a simplification of real growth. Blocks are square and aligned to the tile. Checks are straight radial cracks. Occlusion is a blurred-height estimate.
