# Cushion moss

Bright green cushion moss, dry olive moss, red and green bog moss or fruiting moss with spore capsules. Cushions are Voronoi cells whose borders are only partly shown, gated by noise, so neighbouring mounds merge in places and part along dark crevices elsewhere.

Each shoot tip is a tiny dome from a fine Voronoi diagram, roughened by fibre noise. Colour runs from dark in the crevices to light at the tips, `dryness` browns the tips and `capsules` adds spore stalks.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `moss_cushion_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.8 |
| `normal` | `moss_cushion_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `moss_cushion_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.5 to 1 |
| `height` | `moss_cushion_height.png` | 1 | linear | white is high |
| `ao` | `moss_cushion_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Bright green cushion moss.
- `dry_olive`: Dry olive-brown moss in summer.
- `sphagnum`: Red and green bog moss with large soft heads.
- `fruiting`: Green moss with spore stalks and capsules.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `clumps` | int | 4 | 1 to 12 | Noise cells across the tile for the cushion mounds. |
| `shoots_across` | int | 90 | 24 to 220 | Shoot tips across the tile (higher is finer). |
| `mound_height` | float | 0.6 | 0 to 1 | Height of the mounds relative to the shoot detail. |
| `crevices` | float | 0.5 | 0 to 1 | Depth and darkness of the gaps between mounds. |
| `dryness` | float | 0 | 0 to 1 | Browned, dry tips. |
| `capsules` | float | 0 | 0 to 1 | Spore stalks with capsules standing above the moss. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`moss_cushion.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python moss_cushion.py --size 1024 --seed 7 --preset dry_olive --out textures/moss_cushion
python moss_cushion.py --width 512 --height 256 --set clumps=12 --orm --out maps
```

`--orm` also writes `moss_cushion_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import moss_cushion

maps = moss_cushion.generate(512, 512, seed=3, preset="dry_olive")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 27.3 s (19 s to compute, 8.3 s to write the PNG files) with a peak of about 954 MB; 256 x 256 takes about 1.85 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/moss_cushion/` of your project (for example `python moss_cushion.py --size 1024 --out path/to/project/baltor/textures/moss_cushion`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.02, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Shoots are tiny Voronoi domes, which read as moss at moderate distance but have no individual leaves. Capsule stalks lie flat in the height map. Occlusion is a blurred-height estimate.
