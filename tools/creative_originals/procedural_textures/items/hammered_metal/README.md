# Hand-hammered metal

Polished copper, aged copper with patina, soft grey pewter, planished brass or bright silver. Each hammer blow is a cell of a jittered Voronoi diagram; inside a cell the surface is a shallow spherical cap around the blow's centre, so neighbouring dimples meet in soft ridges along the cell borders.

The ridges catch the polish and stay bright, while aged presets let a dark patina settle in the dimples (`patina`). A second, finer set of blows can overlay the first, as on planished work (`planishing`).

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `hammered_metal_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.98 |
| `normal` | `hammered_metal_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `hammered_metal_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 0.9 |
| `metallic` | `hammered_metal_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `hammered_metal_height.png` | 1 | linear | white is high |
| `ao` | `hammered_metal_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Polished hammered copper.
- `aged_copper`: Hammered copper darkened with patina in the dimples.
- `pewter`: Soft grey hammered pewter with small, regular blows.
- `brass_planished`: Brass with fine planishing marks over larger dimples.
- `silver`: Bright hammered silver with deep, large dimples.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `dimples_across` | int | 9 | 3 to 30 | Hammer blows across the tile. |
| `dimple_depth` | float | 0.6 | 0.1 to 1 | Depth of the dimples. |
| `irregularity` | float | 0.85 | 0 to 1 | How far blows stray from a regular grid. |
| `planishing` | float | 0.3 | 0 to 1 | Second layer of smaller, shallower blows. |
| `patina` | float | 0 | 0 to 1 | Dark oxide settled in the dimples. |
| `polish` | float | 0.7 | 0 to 1 | Polish of the ridges and the metal overall. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`hammered_metal.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python hammered_metal.py --size 1024 --seed 7 --preset aged_copper --out textures/hammered_metal
python hammered_metal.py --width 512 --height 256 --set dimples_across=30 --orm --out maps
```

`--orm` also writes `hammered_metal_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import hammered_metal

maps = hammered_metal.generate(512, 512, seed=3, preset="aged_copper")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 32.9 s (17.6 s to compute, 15.3 s to write the PNG files) with a peak of about 776 MB; 256 x 256 takes about 1.92 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/hammered_metal/` of your project (for example `python hammered_metal.py --size 1024 --out path/to/project/baltor/textures/hammered_metal`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Every blow is a spherical cap on a Voronoi cell, an idealization of real blows, which vary in angle, force and overlap. Patina is a colour and roughness layer without its own relief. Occlusion is a blurred-height estimate, not ray traced.
