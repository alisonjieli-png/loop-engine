# Cracked earth and salt flat

Dry tan clay, dark drying mud, a pale desert pan or a white salt flat. Plates are cells of a Voronoi diagram on the torus. With `edge_relief` below zero the cell borders open as cracks whose width wanders with noise, and plate edges curl up as the mud shrinks; a finer diagram adds shallow secondary cracks.

With `edge_relief` above zero the borders rise into ridges instead, as salt crust does on a dry lake. `moisture` darkens and smooths damp patches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `cracked_earth_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.9 |
| `normal` | `cracked_earth_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `cracked_earth_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `cracked_earth_height.png` | 1 | linear | white is high |
| `ao` | `cracked_earth_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Dry tan clay plates with open cracks and curled edges.
- `dark_mud`: Dark drying mud with narrow cracks and damp patches.
- `desert_pan`: Pale desert pan with wide cracks and many small plates.
- `salt_flat`: White salt crust in polygons with raised ridges.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `plates_across` | int | 6 | 2 to 20 | Plates across the tile. |
| `crack_width` | float | 0.07 | 0.01 to 0.25 | Crack (or ridge) width in plate widths. |
| `edge_relief` | float | -0.8 | -1 to 1 | Border profile: negative opens cracks with curled plate edges, positive raises salt ridges. |
| `curl` | float | 0.5 | 0 to 1 | How far plate edges lift beside the cracks. |
| `secondary_cracks` | float | 0.5 | 0 to 1 | Shallow finer cracks inside the plates. |
| `moisture` | float | 0 | 0 to 1 | Damp darkening and lower roughness in patches. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`cracked_earth.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python cracked_earth.py --size 1024 --seed 7 --preset dark_mud --out textures/cracked_earth
python cracked_earth.py --width 512 --height 256 --set plates_across=20 --orm --out maps
```

`--orm` also writes `cracked_earth_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import cracked_earth

maps = cracked_earth.generate(512, 512, seed=3, preset="dark_mud")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 26 s (17 s to compute, 9 s to write the PNG files) with a peak of about 766 MB; 256 x 256 takes about 1.69 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/cracked_earth/` of your project (for example `python cracked_earth.py --size 1024 --out path/to/project/baltor/textures/cracked_earth`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 2). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.025, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Plates are Voronoi cells, which give mostly polygonal outlines; real shrinkage cracks also meet at right angles. Curl and ridges are height profiles only. Occlusion is a blurred-height estimate.
