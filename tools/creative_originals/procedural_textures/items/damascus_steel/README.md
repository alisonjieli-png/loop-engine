# Damascus pattern-welded steel

Random-pattern, ladder, raindrop and chevron Damascus, and a deep coffee etch with near-black layers. A billet of alternating bright and dark steel is forged, cut and ground, and the blade face shows where the ground plane cuts the distorted stack: the visible bands are contour lines of a layer phase, a whole number of layer pairs down the tile plus a periodic displacement, so the pattern repeats.

The displacement is a domain-warped fractal for the random pattern (contours fold into loops and eyes), narrow grooves for the ladder pattern, smooth dimples for raindrops and a triangle wave for chevrons; `randomness` mixes some folding into the regular patterns, and `thickness_variation` lets layers thicken and thin. Where bands get finer than about two pixels, a pixel fades to the local share of bright layer instead of aliasing. Etching darkens, lowers and roughens the dark layers; grinding leaves faint lines along the blade.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `damascus_steel_albedo.png` | 3 | sRGB | glTF base colour, values 0.08 to 0.95 |
| `normal` | `damascus_steel_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `damascus_steel_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.08 to 0.9 |
| `metallic` | `damascus_steel_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `damascus_steel_height.png` | 1 | linear | white is high |
| `ao` | `damascus_steel_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Random-pattern Damascus with folded contours, medium etch.
- `ladder`: Ladder pattern: regular rungs where grooves were cut across the billet.
- `raindrop`: Raindrop pattern: concentric rings around drilled dimples.
- `chevron`: Chevron pattern from a restacked billet, light satin etch.
- `coffee_etch`: Deep coffee etch: near-black layers and bright nickel lines, fine stack.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 3 | Pattern: 0 random, 1 ladder, 2 raindrop, 3 chevron. |
| `layers` | int | 24 | 4 to 160 | Layer pairs down the tile (bright and dark layer together). |
| `distortion` | float | 4 | 0 to 16 | How far the forging displaces the layers, in layer pairs. |
| `features` | int | 4 | 1 to 16 | Ladder rungs, raindrop dimples or chevrons across the tile. |
| `randomness` | float | 0.35 | 0 to 1 | Share of random folding added to the ladder, raindrop and chevron patterns. |
| `thickness_variation` | float | 0.35 | 0 to 1 | How much the bright layers thicken and thin across the blade. |
| `etch` | float | 0.6 | 0 to 1 | Etch depth: contrast and relief between the layer kinds. |
| `grind_lines` | float | 0.3 | 0 to 1 | Fine grinding lines along the blade (across the tile). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.2 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`damascus_steel.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python damascus_steel.py --size 1024 --seed 7 --preset ladder --out textures/damascus_steel
python damascus_steel.py --width 512 --height 256 --set pattern=3 --orm --out maps
```

`--orm` also writes `damascus_steel_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import damascus_steel

maps = damascus_steel.generate(512, 512, seed=3, preset="ladder")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 18.6 s (10.9 s to compute, 7.6 s to write the PNG files) with a peak of about 761 MB; 256 x 256 takes about 1.26 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/damascus_steel/` of your project (for example `python damascus_steel.py --size 1024 --out path/to/project/baltor/textures/damascus_steel`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The pattern is a contour model of a distorted layer stack, not a forging simulation; ladder, raindrop and chevron are idealized versions of the smith's grooves, dimples and restacking. Layers finer than about two pixels fade to their average tone instead of drawing, so very fine stacks need a large texture. The etch relief is shallow and best carried by the normal map. Occlusion is a blurred-height estimate, not ray traced.
