# Terrazzo

Classic white terrazzo with mixed marble chips, warm Venetian terrazzo with large dense chips, pink pastel, charcoal noir or grey with glass shards. Chips are irregular polygons: each has five to nine vertices at random radii around its centre.

Chip sizes follow a log-uniform spread between `smallest` and `largest`, and chips are painted largest first so small ones settle between them. The matrix carries fine sand speckle and tiny pores, and `polish` sets the finish from honed to polished.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `terrazzo_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `terrazzo_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `terrazzo_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `height` | `terrazzo_height.png` | 1 | linear | white is high |
| `ao` | `terrazzo_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White cement with mixed grey, black, rust and white marble chips.
- `venetian`: Warm matrix with large, dense marble chips in reds and creams.
- `pastel`: Pink matrix with sparse pastel chips.
- `noir`: Charcoal matrix with white and grey chips.
- `glass_honed`: Grey matrix with green and blue glass shards, honed.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `chips` | int | 260 | 20 to 1200 | Number of chips on the tile. |
| `smallest` | float | 0.006 | 0.002 to 0.05 | Smallest chip radius in texture units. |
| `largest` | float | 0.03 | 0.004 to 0.12 | Largest chip radius in texture units. |
| `angularity` | float | 0.5 | 0 to 1 | How jagged the chip outlines are (0 rounded pebbles, 1 sharp shards). |
| `polish` | float | 0.8 | 0 to 1 | Surface finish from honed (0) to polished (1). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`terrazzo.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python terrazzo.py --size 1024 --seed 7 --preset venetian --out textures/terrazzo
python terrazzo.py --width 512 --height 256 --set chips=1200 --orm --out maps
```

`--orm` also writes `terrazzo_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import terrazzo

maps = terrazzo.generate(512, 512, seed=3, preset="venetian")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 15.4 s (7.3 s to compute, 8.2 s to write the PNG files) with a peak of about 569 MB; 256 x 256 takes about 1 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/terrazzo/` of your project (for example `python terrazzo.py --size 1024 --out path/to/project/baltor/textures/terrazzo`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.6) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Chips are random polygons that may overlap; real terrazzo is packed by casting and grinding. Chip colours are flat with slight variation and no internal veining. Relief is very shallow. Occlusion is a blurred-height estimate.
