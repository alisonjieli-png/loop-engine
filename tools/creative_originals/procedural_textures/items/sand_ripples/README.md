# Sand ripples and dunes

Dry beach sand, a wet tidal flat, orange desert dunes or white gypsum sand. Ripples follow a phase that advances a whole number of cycles across the tile along an integer direction, and smooth noise bends the phase so crests curve, fork and merge.

The profile is asymmetric, with a long gentle slope and a short steep face as wind or current builds them. Heavy dark minerals collect in the troughs, `dune_swell` adds low dunes under the ripples, and `wetness` darkens and smooths the sand.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `sand_ripples_albedo.png` | 3 | sRGB | glTF base colour, values 0.05 to 0.9 |
| `normal` | `sand_ripples_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `sand_ripples_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.2 to 1 |
| `height` | `sand_ripples_height.png` | 1 | linear | white is high |
| `ao` | `sand_ripples_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Dry beach sand with wind ripples.
- `tidal_wet`: Wet tidal flat with symmetric ripples and dark troughs.
- `desert_dunes`: Orange desert sand with dune swells and fine ripples.
- `white_gypsum`: White gypsum sand with long straight ripples.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `ripples` | int | 12 | 2 to 48 | Ripple crests across the tile along the ripple direction. |
| `direction` | int | 0 | 0 to 3 | Crest direction: 0 vertical crests, 1 horizontal crests, 2 and 3 the two diagonals. |
| `meander` | float | 0.5 | 0 to 1 | How much crests bend, fork and merge. |
| `asymmetry` | float | 0.7 | 0 to 0.95 | Share of each ripple taken by the gentle slope (0.5 symmetric, higher is wind-built). |
| `dune_swell` | float | 0 | 0 to 1 | Large low dunes under the ripples. |
| `trough_minerals` | float | 0.4 | 0 to 1 | Dark heavy minerals collected in the troughs. |
| `wetness` | float | 0 | 0 to 1 | Wet sand: darker and smoother. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`sand_ripples.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python sand_ripples.py --size 1024 --seed 7 --preset tidal_wet --out textures/sand_ripples
python sand_ripples.py --width 512 --height 256 --set ripples=48 --orm --out maps
```

`--orm` also writes `sand_ripples_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import sand_ripples

maps = sand_ripples.generate(512, 512, seed=3, preset="tidal_wet")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 18.9 s (10.9 s to compute, 8.1 s to write the PNG files) with a peak of about 640 MB; 256 x 256 takes about 1.22 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/sand_ripples/` of your project (for example `python sand_ripples.py --size 1024 --out path/to/project/baltor/textures/sand_ripples`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.012, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Ripple direction is limited to four whole-tile directions so the texture repeats. Ripples are a phase field, not a sediment simulation, and do not respond to obstacles. Dune swells are low-frequency height only. Occlusion is a blurred-height estimate.
