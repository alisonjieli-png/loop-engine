# Keeled snake scales with body patterns

Olive python skin with dark-edged blotches, banded red, black and yellow scales, dusty brown skin with light-rimmed dorsal diamonds, or bright green smooth scales with a fine speckle. Scales sit in offset rows with whole counts across and down, so the skin tiles, and each scale slips under the row above it.

`scales` and `elongation` set scale count and shape, `overlap` how much skin shows between scales, and `keel` the ridge along each scale. `pattern` chooses blotches, bands, diamonds or a speckle, evaluated once per scale so the markings follow the scale grid; `pattern_repeat` sets their scale and `gloss` how freshly shed the skin looks.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `snake_scales_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `snake_scales_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `snake_scales_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `height` | `snake_scales_height.png` | 1 | linear | white is high |
| `ao` | `snake_scales_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Olive and tan python skin with dark-edged blotches.
- `coral_banded`: Banded red, black and yellow scales, smooth and glossy.
- `diamondback`: Dusty brown skin with dark dorsal diamonds and strong keels.
- `green_tree`: Bright green smooth scales with a fine speckle.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `scales` | int | 14 | 6 to 32 | Scale columns across the tile; rows follow from the scale length. |
| `elongation` | float | 1.35 | 0.9 to 2.2 | Scale length divided by width. |
| `overlap` | float | 0.6 | 0 to 1 | How much scales overlap; low values show the skin between them. |
| `keel` | float | 0.6 | 0 to 1 | Height of the ridge along each scale (0 for smooth scales). |
| `pattern` | int | 0 | 0 to 3 | 0 blotches with dark outlines, 1 cross bands, 2 dorsal diamonds, 3 plain with a fine speckle. |
| `pattern_repeat` | int | 2 | 1 to 6 | How many times the body pattern repeats across the tile. |
| `gloss` | float | 0.5 | 0 to 1 | Shine of the scales: 0 dry and matte, 1 freshly shed and glossy. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`snake_scales.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python snake_scales.py --size 1024 --seed 7 --preset coral_banded --out textures/snake_scales
python snake_scales.py --width 512 --height 256 --set scales=32 --orm --out maps
```

`--orm` also writes `snake_scales_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import snake_scales

maps = snake_scales.generate(512, 512, seed=3, preset="coral_banded")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17.9 s (10.4 s to compute, 7.5 s to write the PNG files) with a peak of about 518 MB; 256 x 256 takes about 1.02 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/snake_scales/` of your project (for example `python snake_scales.py --size 1024 --out path/to/project/baltor/textures/snake_scales`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Scales are rounded-diamond height fields of one size in regular offset rows; belly scutes, head plates and the change of scale size around the body are out of scope. The body axis runs along V with the head toward the top. Patterns are stylized fields sampled at scale centres, not the markings of real species, and there is no iridescence or shedding skin. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic.
