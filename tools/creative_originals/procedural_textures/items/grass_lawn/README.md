# Grass from above

A mown lawn, a meadow with clover flowers, parched summer grass or dense dark turf. Each blade is a tapered stroke from its root, pointing in a random direction with a slight common lean, rising toward the middle and drooping at the tip.

Blades are painted with a z-buffer, so a pixel keeps the highest blade with that blade's colour from dark base to lighter tip, and blades cross and occlude each other. Soil shows through sparse turf, `dryness` mixes in straw-coloured blades and `flowers` dots the lawn.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `grass_lawn_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.85 |
| `normal` | `grass_lawn_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `grass_lawn_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.35 to 1 |
| `height` | `grass_lawn_height.png` | 1 | linear | white is high |
| `ao` | `grass_lawn_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Mown lawn: dense short green blades.
- `meadow`: Long meadow grass with dry blades and clover flowers.
- `dry_summer`: Parched straw-coloured grass with bare soil.
- `lush_dark`: Dense, dark, well-watered turf.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `blades` | int | 4800 | 200 to 12000 | Number of blades on the tile. |
| `blade_length` | float | 0.042 | 0.008 to 0.12 | Average blade length in texture units. |
| `blade_width` | float | 0.0034 | 0.001 to 0.01 | Blade width at the base in texture units. |
| `lean` | float | 0.3 | 0 to 1 | How strongly blades lean one way, as after mowing or wind. |
| `dryness` | float | 0.1 | 0 to 1 | Share of straw-coloured dry blades. |
| `flowers` | float | 0 | 0 to 1 | Small clover flowers in the turf. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`grass_lawn.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python grass_lawn.py --size 1024 --seed 7 --preset meadow --out textures/grass_lawn
python grass_lawn.py --width 512 --height 256 --set blades=12000 --orm --out maps
```

`--orm` also writes `grass_lawn_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import grass_lawn

maps = grass_lawn.generate(512, 512, seed=3, preset="meadow")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 26 s (12.8 s to compute, 13.2 s to write the PNG files) with a peak of about 542 MB; 256 x 256 takes about 1.65 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/grass_lawn/` of your project (for example `python grass_lawn.py --size 1024 --out path/to/project/baltor/textures/grass_lawn`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.01, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Blades are flat strokes in a height map, so the texture suits ground seen from above or at a distance; close views need geometry or alpha cards. At small sizes blades are under a few pixels wide and read as speckle. Occlusion is a blurred-height estimate.
