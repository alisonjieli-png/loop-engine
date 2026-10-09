# Science fiction greeble panels

Grey panelling with cyan light strips, dense machinery with many grilles, a clean white corridor with warm lights or dark hazard panels with red lights. The tile is split again and again into rectangles (`depth`, `split_chance`), each cut snapped to a 1/32 grid, so the tile edges are always seams and the layout repeats.

Every leaf rectangle is a panel with its own level and a bevelled rim, and a hash of the panel picks its detail: plain, grille slots, corner bolts, a light strip or a recessed port. Scuffs wear paint to bare metal near the rims, which the metallic map follows; light strips glow in the emissive map.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `scifi_greeble_panels_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `scifi_greeble_panels_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `scifi_greeble_panels_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.12 to 1 |
| `metallic` | `scifi_greeble_panels_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `scifi_greeble_panels_height.png` | 1 | linear | white is high |
| `ao` | `scifi_greeble_panels_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `scifi_greeble_panels_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey panelling with cyan light strips.
- `dense_machinery`: Deep, dense subdivision with many grilles.
- `corridor_white`: Clean white corridor panels with warm light strips.
- `hazard_dark`: Dark panels with red lights and heavy seams.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `depth` | int | 5 | 2 to 8 | Subdivision depth: more levels give more, smaller panels. |
| `split_chance` | float | 0.8 | 0.3 to 1 | Chance that a panel above the minimum size splits again. |
| `seam` | float | 0.004 | 0.001 to 0.012 | Seam half-width in texture units. |
| `level_variation` | float | 0.6 | 0 to 1 | Height difference between panels. |
| `lights` | float | 0.15 | 0 to 1 | Share of panels with a light strip. |
| `grilles` | float | 0.2 | 0 to 1 | Share of panels with grille slots. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and lights in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`scifi_greeble_panels.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python scifi_greeble_panels.py --size 1024 --seed 7 --preset dense_machinery --out textures/scifi_greeble_panels
python scifi_greeble_panels.py --width 512 --height 256 --set depth=8 --orm --out maps
```

`--orm` also writes `scifi_greeble_panels_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import scifi_greeble_panels

maps = scifi_greeble_panels.generate(512, 512, seed=3, preset="dense_machinery")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 24.5 s (12.3 s to compute, 12.1 s to write the PNG files) with a peak of about 692 MB; 256 x 256 takes about 1.74 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/scifi_greeble_panels/` of your project (for example `python scifi_greeble_panels.py --size 1024 --out path/to/project/baltor/textures/scifi_greeble_panels`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.01, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

## Limits

Panel cuts snap to a 32 by 32 grid, so every panel is an axis-aligned rectangle with no diagonal or rounded panels. One tile holds one subdivision, so a large wall repeats visibly; vary the seed between surfaces. Light strips are emissive colour, not light sources. Occlusion is a blurred-height estimate, not ray traced.
