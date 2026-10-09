# Octagon and dot floor tiles

White glazed octagons with black dots, terracotta with green glazed tozzetti, honed white marble with black marble dots, or a small white mosaic with blue dots. `tiles_across` octagons cross the tile on a square grid, so the floor repeats in both directions.

Each octagon is a square cell with its corners cut at 45 degrees; the four cut corners around every grid point form a dot whose half-diagonal is `dot_size`. A pixel's signed distance to its cell's octagon says whether it lies on the octagon or a dot and how far it is from the joint, which sets the grout, the rounded edge (`bevel`) and small lippage between pieces. `gloss` runs from honed to glossy, `veining` draws marble veins that break at the joints, and `wear` scuffs traffic patches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `octagon_dot_tiles_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `octagon_dot_tiles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `octagon_dot_tiles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `height` | `octagon_dot_tiles_height.png` | 1 | linear | white is high |
| `ao` | `octagon_dot_tiles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White glazed octagons with black dots and grey grout.
- `terracotta_tozzetti`: Unglazed terracotta octagons with small dark green glazed dots.
- `marble_classic`: Honed white marble octagons with black marble dots, thin joints, veins.
- `small_mosaic`: Small matte white octagon mosaic with blue dots.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `tiles_across` | int | 4 | 1 to 14 | Octagons across the tile width (and height). |
| `dot_size` | float | 0.2 | 0.1 to 0.38 | Half-diagonal of each corner dot in octagon widths; larger dots cut deeper corners. |
| `grout_width` | float | 0.02 | 0.004 to 0.08 | Joint width in octagon widths. |
| `grout_depth` | float | 0.45 | 0 to 1 | How far the grout sits below the tile faces. |
| `bevel` | float | 0.03 | 0.005 to 0.12 | Width of the rounded tile edge in octagon widths. |
| `gloss` | float | 0.7 | 0 to 1 | 0 matte or honed, 1 glossy glaze. |
| `veining` | float | 0 | 0 to 1 | Marble veins through the octagons (light) and dots (pale veins on dark stone). |
| `wear` | float | 0.15 | 0 to 1 | Scuffed, duller and lighter traffic patches and slightly worn edges. |
| `colour_variation` | float | 0.35 | 0 to 1 | Spread of tone between pieces. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`octagon_dot_tiles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python octagon_dot_tiles.py --size 1024 --seed 7 --preset terracotta_tozzetti --out textures/octagon_dot_tiles
python octagon_dot_tiles.py --width 512 --height 256 --set tiles_across=14 --orm --out maps
```

`--orm` also writes `octagon_dot_tiles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import octagon_dot_tiles

maps = octagon_dot_tiles.generate(512, 512, seed=3, preset="terracotta_tozzetti")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 23.8 s (16.3 s to compute, 7.5 s to write the PNG files) with a peak of about 559 MB; 256 x 256 takes about 1.41 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/octagon_dot_tiles/` of your project (for example `python octagon_dot_tiles.py --size 1024 --out path/to/project/baltor/textures/octagon_dot_tiles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1). Change `uv1_scale` to repeat the tile.

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

Octagons are regular cuts of a square cell, so octagons and dots always align with the tile axes; borders, cut pieces and diagonal layouts are out of scope. Marble veins are isolines of warped noise, an approximation of real stone, read at a random offset per piece. Lippage between pieces is a small random height offset. Occlusion is a blurred-height estimate, not ray traced.
