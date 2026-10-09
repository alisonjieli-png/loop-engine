# Cracked asphalt

Worn road asphalt, fresh black asphalt, fatigue-cracked pavement, repaired asphalt with tar sealant or a coarse chip seal. Aggregate is a fine Voronoi diagram: each cell is a stone with its own grey, binder fills the borders, and `wear` removes binder from the stone tops.

Main cracks are random walks that wander and branch; `alligator` adds a patch of fatigue cracking from the borders of a coarser Voronoi diagram, `sealant` lays glossy tar strips over the main cracks, and `stains` darkens soft blotches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `asphalt_cracked_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.6 |
| `normal` | `asphalt_cracked_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `asphalt_cracked_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.2 to 1 |
| `height` | `asphalt_cracked_height.png` | 1 | linear | white is high |
| `ao` | `asphalt_cracked_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Worn grey road asphalt with a few long cracks.
- `fresh`: New black asphalt with no cracks.
- `alligator`: Old pavement with fatigue cracking and stains.
- `sealed`: Repaired asphalt with tar sealant over the cracks.
- `coarse_chip`: Coarse chip seal with large, light stones.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `aggregate_size` | int | 80 | 24 to 200 | Aggregate stones across the tile (higher is finer). |
| `cracks` | int | 4 | 0 to 16 | Main cracks wandering across the tile; each may branch. |
| `crack_width` | float | 0.006 | 0.001 to 0.015 | Main crack width in texture units. |
| `alligator` | float | 0 | 0 to 1 | Area of alligator (fatigue) cracking. |
| `sealant` | float | 0 | 0 to 1 | Glossy tar sealant painted over the main cracks. |
| `wear` | float | 0.5 | 0 to 1 | Binder worn off the stone tops: 0 fresh black, 1 old grey. |
| `stains` | float | 0.3 | 0 to 1 | Oil and water stains. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`asphalt_cracked.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python asphalt_cracked.py --size 1024 --seed 7 --preset fresh --out textures/asphalt_cracked
python asphalt_cracked.py --width 512 --height 256 --set aggregate_size=200 --orm --out maps
```

`--orm` also writes `asphalt_cracked_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import asphalt_cracked

maps = asphalt_cracked.generate(512, 512, seed=3, preset="fresh")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 22.3 s (14.8 s to compute, 7.5 s to write the PNG files) with a peak of about 666 MB; 256 x 256 takes about 1.56 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/asphalt_cracked/` of your project (for example `python asphalt_cracked.py --size 1024 --out path/to/project/baltor/textures/asphalt_cracked`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

There are no lane markings, potholes or curbs. Cracks are random walks and fatigue cracks are Voronoi borders, approximations of real failure patterns. Aggregate stones are flat Voronoi cells. Occlusion is a blurred-height estimate.
