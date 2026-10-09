# Quilted and deep-buttoned fabric

A cream cotton bedspread, glossy black puffer-jacket channels, blush satin squares, oxblood deep-buttoned leather or a navy moving blanket. The seams are line families whose phases change by whole numbers across the tile, so every seam closes on itself and the quilt tiles in both directions.

Each panel puffs between its seams by `puff`; `cells` and `aspect` set how many panels fit across and down. `stitches` lays dashes along the seams (0 leaves a plain fold), `buttons` pulls a domed button deep into every seam crossing, `wrinkles` crinkles the cover near the seams, `sheen` polishes the taut panel tops and `weave` adds a fine cloth grain.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `quilted_fabric_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `quilted_fabric_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `quilted_fabric_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `height` | `quilted_fabric_height.png` | 1 | linear | white is high |
| `ao` | `quilted_fabric_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Cream cotton bedspread in diamond quilting with visible stitches.
- `puffer_channel`: Black nylon puffer-jacket channels, glossy and crinkled.
- `square_satin`: Blush satin in a square grid with fine stitching.
- `chesterfield`: Deep-buttoned oxblood leather tufting: full diamonds, buttons, no stitches.
- `moving_blanket`: Navy workwear quilting: small diamonds with contrast stitching.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 2 | 0 diamond quilting (two diagonal seam families), 1 square grid, 2 horizontal channels. |
| `cells` | int | 5 | 1 to 16 | Quilted panels across the tile width (diamonds, squares, or for channels the channel count down the tile). |
| `aspect` | float | 1.4 | 0.5 to 2.5 | Panels down the tile per panel across; above 1 the diamonds are taller than wide. |
| `puff` | float | 0.6 | 0.1 to 1 | How full the panels are between the seams. |
| `stitches` | int | 9 | 0 to 30 | Stitches along one panel edge; 0 hides the seams' stitching (tufting folds). |
| `buttons` | float | 0 | 0 to 1 | Size of the buttons pulled deep into the seam crossings, as in deep-buttoned upholstery. |
| `wrinkles` | float | 0.3 | 0 to 1 | Crinkles of the fabric gathered near the seams. |
| `sheen` | float | 0 | 0 to 1 | Gloss of taut panel tops: 0 matte cotton, 1 shiny nylon or satin. |
| `weave` | float | 0.5 | 0 to 1 | Fine woven texture of the cover fabric. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`quilted_fabric.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python quilted_fabric.py --size 1024 --seed 7 --preset puffer_channel --out textures/quilted_fabric
python quilted_fabric.py --width 512 --height 256 --set pattern=2 --orm --out maps
```

`--orm` also writes `quilted_fabric_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import quilted_fabric

maps = quilted_fabric.generate(512, 512, seed=3, preset="puffer_channel")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 21.8 s (9.7 s to compute, 12.1 s to write the PNG files) with a peak of about 560 MB; 256 x 256 takes about 1.21 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/quilted_fabric/` of your project (for example `python quilted_fabric.py --size 1024 --out path/to/project/baltor/textures/quilted_fabric`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.03, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Panels are pillow profiles between straight seam lines, not cloth simulation: there is no drape, gathering or sagging, and tufting folds follow the seams instead of radiating from each button. Diamonds keep whole panel counts across and down the tile, so the aspect is quantized. Stitches are dashes in the seam groove; thread twist is not modelled. The weave is a fine cosine grid that fades out when it would be finer than a few pixels. Occlusion is a blurred-height estimate, not ray traced.
