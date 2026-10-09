# Plaster and stucco finishes

White knockdown, terracotta or grey Venetian plaster, warm sand-float lime render or heavy cream knockdown. `style` picks the finish: knockdown stamps ragged splatter blobs and cuts them flat at a common level; Venetian lays long curved swaths in translucent layers and burnishes them; sand float leaves fine grain and faint arcs from the float.

`density`, `feature_size` and `relief` scale the blobs, swaths or arcs, and `tone_variation` mixes in the preset's second colour.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `plaster_stucco_albedo.png` | 3 | sRGB | glTF base colour, values 0.04 to 0.92 |
| `normal` | `plaster_stucco_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `plaster_stucco_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.08 to 1 |
| `height` | `plaster_stucco_height.png` | 1 | linear | white is high |
| `ao` | `plaster_stucco_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White painted knockdown ceiling texture.
- `venetian_terracotta`: Burnished terracotta Venetian plaster.
- `venetian_grey`: Cool grey polished Venetian plaster.
- `sand_lime`: Warm lime render with a sand float finish.
- `heavy_knockdown`: Coarse cream knockdown with large flattened blobs.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `style` | int | 0 | 0 to 2 | Finish: 0 knockdown, 1 Venetian trowel, 2 sand float. |
| `density` | float | 0.5 | 0 to 1 | Number of blobs, swaths or float arcs. |
| `feature_size` | float | 0.05 | 0.01 to 0.15 | Typical blob or swath size in texture units. |
| `relief` | float | 0.6 | 0 to 1 | Height of blobs and ridges. |
| `tone_variation` | float | 0.3 | 0 to 1 | Colour variation between swaths and across the wall. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`plaster_stucco.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python plaster_stucco.py --size 1024 --seed 7 --preset venetian_terracotta --out textures/plaster_stucco
python plaster_stucco.py --width 512 --height 256 --set style=2 --orm --out maps
```

`--orm` also writes `plaster_stucco_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import plaster_stucco

maps = plaster_stucco.generate(512, 512, seed=3, preset="venetian_terracotta")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17.6 s (9.3 s to compute, 8.3 s to write the PNG files) with a peak of about 607 MB; 256 x 256 takes about 0.93 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/plaster_stucco/` of your project (for example `python plaster_stucco.py --size 1024 --out path/to/project/baltor/textures/plaster_stucco`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Each finish is an approximation: knockdown blobs are flattened stamps, Venetian layers are translucent ellipse swaths, and sand float arcs are drawn strokes. Paint and lime colour are uniform apart from these effects. Occlusion is a blurred-height estimate.
