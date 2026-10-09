# Camouflage prints on twill: woodland, digital, tiger, desert, splinter

Woodland with khaki ground, brown and green blobs and black branches; digital woodland stepped into small square cells; long ragged tiger stripes; three-colour desert with small dark and white rock spots; or splinter shards in three colours under short vertical rain dashes. Every family is a stack of colour layers over a base: a pixel takes the colour of the topmost layer whose field exceeds the layer's threshold, and thresholds come from quantiles of each field, so a layer covers the same share of the cloth whatever the seed.

The fields differ by family: domain-warped fractal noise for blobs, a ridged field for branches, the same fields sampled once per grid cell with edge dithering for digital, a lattice stretched along the width for stripes, Worley cells for spots and for whole-cell shards. The cloth beneath is a twill-like weave of diagonal ridges at a whole number of threads, which shapes height, normals and slight groove shading; `fading` pales the print in washed-out patches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `camouflage_patterns_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.85 |
| `normal` | `camouflage_patterns_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `camouflage_patterns_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.5 to 1 |
| `height` | `camouflage_patterns_height.png` | 1 | linear | white is high |
| `ao` | `camouflage_patterns_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Woodland: khaki ground with brown and green blobs and black branches.
- `digital_pixels`: Digital woodland: the same layering stepped into small square pixels.
- `tiger_stripe`: Tiger stripe: long ragged horizontal stripes over a pale green ground.
- `desert_spots`: Three-colour desert with soft blobs and small dark and white rock spots.
- `splinter_rain`: Splinter: straight-edged shards in three colours under short rain dashes.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 4 | 0 woodland blobs and branches, 1 digital pixels, 2 tiger stripes, 3 desert with spots, 4 splinter with rain dashes. |
| `blobs` | int | 4 | 2 to 12 | Pattern features across the tile; larger values give smaller shapes. |
| `pixels_across` | int | 64 | 16 to 160 | Square cells across the tile for the digital pattern. |
| `ragged` | float | 0.5 | 0 to 1 | Raggedness of the shape edges (domain warping). |
| `threads` | int | 96 | 24 to 240 | Twill threads across the tile. |
| `weave` | float | 0.6 | 0 to 1 | Strength of the twill texture in colour and relief. |
| `fading` | float | 0.15 | 0 to 1 | Washed-out wear that pales the print in patches. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`camouflage_patterns.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python camouflage_patterns.py --size 1024 --seed 7 --preset digital_pixels --out textures/camouflage_patterns
python camouflage_patterns.py --width 512 --height 256 --set pattern=4 --orm --out maps
```

`--orm` also writes `camouflage_patterns_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import camouflage_patterns

maps = camouflage_patterns.generate(512, 512, seed=3, preset="digital_pixels")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 19.5 s (12.2 s to compute, 7.4 s to write the PNG files) with a peak of about 656 MB; 256 x 256 takes about 1.21 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/camouflage_patterns/` of your project (for example `python camouflage_patterns.py --size 1024 --out path/to/project/baltor/textures/camouflage_patterns`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.8) and the height map through a Displacement node (scale 0.001, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The five families are invented in the general style of their kind and do not reproduce any issued or trademarked pattern. Layer shapes come from noise fields cut at quantiles, so they are statistically, not exactly, like printed screens. The weave is a pair of diagonal sine ridges at a whole number of threads across the tile, not a modelled twill; it aliases below about three pixels per thread. Fading is a noise mask, not a wear simulation. Occlusion is a blurred-height estimate.
