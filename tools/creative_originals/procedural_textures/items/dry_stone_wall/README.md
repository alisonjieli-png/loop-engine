# Dry stone wall of stacked irregular slabs

A grey limestone field wall, mossy brown gritstone, thin coursed slate or chunky rubble. `courses` rough courses of random height fill the tile, and each course is split into stones of about `stone_length` that wrap around the tile width, so the wall repeats in both directions.

Every stone is a slab: a rotated, tapered rounded rectangle whose outline is roughened by noise, shrunk from its slot by `gap` so dark voids open between neighbours. `tilt` turns the stones out of level and `irregularity` varies their size, thickness and outline. `chinking` wedges small stones into the joints, `lichen` adds pale patches on the faces and `moss` grows in the crevices and along lower edges.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `dry_stone_wall_albedo.png` | 3 | sRGB | glTF base colour, values 0.01 to 0.88 |
| `normal` | `dry_stone_wall_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `dry_stone_wall_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.45 to 1 |
| `height` | `dry_stone_wall_height.png` | 1 | linear | white is high |
| `ao` | `dry_stone_wall_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey limestone field wall with lichen spots and chinking stones.
- `gritstone_moss`: Brown gritstone in thick courses, mossy crevices, few chinks.
- `slate_coursed`: Thin dark slate slabs in many tight courses.
- `rubble_rough`: Rough, chunky rubble with wide voids, heavy tilt and many chinks.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `courses` | int | 7 | 3 to 16 | Rough courses of stones across the tile height. |
| `stone_length` | float | 0.22 | 0.08 to 0.45 | Mean stone length in tile widths. |
| `irregularity` | float | 0.55 | 0 to 1 | Variation of stone size, thickness and outline. |
| `tilt` | float | 0.4 | 0 to 1 | Random rotation of the stones out of level. |
| `gap` | float | 0.4 | 0 to 1 | Width of the dark voids between stones. |
| `chinking` | float | 0.5 | 0 to 1 | Small filler stones wedged into the joints. |
| `face_relief` | float | 0.5 | 0 to 1 | Roughness of the stone faces. |
| `moss` | float | 0.2 | 0 to 1 | Moss in the crevices and on the lower edges of stones. |
| `lichen` | float | 0.3 | 0 to 1 | Pale lichen colonies on the faces. |
| `colour_variation` | float | 0.6 | 0 to 1 | Spread of colour between stones. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`dry_stone_wall.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python dry_stone_wall.py --size 1024 --seed 7 --preset gritstone_moss --out textures/dry_stone_wall
python dry_stone_wall.py --width 512 --height 256 --set courses=16 --orm --out maps
```

`--orm` also writes `dry_stone_wall_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import dry_stone_wall

maps = dry_stone_wall.generate(512, 512, seed=3, preset="gritstone_moss")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 28.4 s (18.8 s to compute, 9.7 s to write the PNG files) with a peak of about 650 MB; 256 x 256 takes about 2.01 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/dry_stone_wall/` of your project (for example `python dry_stone_wall.py --size 1024 --out path/to/project/baltor/textures/dry_stone_wall`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 2.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.03, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Stones are rotated, tapered rounded rectangles with noisy outlines in rough courses; there are no through stones, coping, batter or stones that cross courses. Voids are drawn as flat dark recesses, and chinks are small ellipses. Lichen and moss are noise patches, not grown. Occlusion is a blurred-height estimate, not ray traced; deep voids read best with the height map for parallax or displacement.
