# Penny round mosaic in hexagonal or square packing

White glossy pennies, matte white with black accents, a hand-set sage blend or unglazed speckled terracotta on a square grid. `columns` sets how many rounds cross the tile and `packing` chooses hexagonal close packing (the even row count closest to a regular lattice) or a square grid, so the sheet repeats in both directions.

Each pixel finds the nearest of four candidate rounds, whose centres and radii stray by `handmade`, and measures the distance to its rim. That distance shapes a bullnose edge, a face that bulges by `dome` and a darker ring where glaze pools, while grout fills the space between at `grout_depth`. `pattern` picks a weighted random blend, a base colour with `accent_share` accents, or clusters that drift through the palette. `glaze` runs from matte porcelain to a glossy glaze.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `penny_round_mosaic_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `penny_round_mosaic_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `penny_round_mosaic_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 1 |
| `height` | `penny_round_mosaic_height.png` | 1 | linear | white is high |
| `ao` | `penny_round_mosaic_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White glossy penny rounds in hexagonal packing with mid grey grout.
- `salt_pepper`: Matte white rounds with scattered black ones and white grout.
- `sage_blend`: Glossy green rounds drifting between sage and moss, uneven hand-set rows.
- `porcelain_grid`: Unglazed speckled terracotta rounds on a square grid with dark grout.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `columns` | int | 12 | 4 to 40 | Rounds across the tile width. |
| `packing` | int | 0 | 0 to 1 | 0 hexagonal close packing (rows offset by half a round), 1 square grid. |
| `pattern` | int | 0 | 0 to 2 | Colour rule: 0 weighted random blend of the palette, 1 a base colour with scattered accents, 2 clusters that drift between the palette colours. |
| `gap` | float | 0.12 | 0.03 to 0.4 | Grout between neighbouring rounds as a share of the round spacing. |
| `dome` | float | 0.6 | 0 to 1 | How much each round's face bulges toward its centre. |
| `handmade` | float | 0.35 | 0 to 1 | Random offsets and size changes of the rounds, as on hand-set sheets. |
| `grout_depth` | float | 0.5 | 0 to 1 | How far the grout sits below the rounds. |
| `accent_share` | float | 0.15 | 0 to 1 | Share of accent rounds (pattern 1) or of the second colour in the random blend (pattern 0). |
| `glaze` | float | 0.85 | 0 to 1 | 0 unglazed matte porcelain, 1 glossy glaze. |
| `colour_variation` | float | 0.35 | 0 to 1 | Spread of tone between rounds of one colour. |
| `dirt` | float | 0.15 | 0 to 1 | Darkening of the grout and the round edges. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`penny_round_mosaic.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python penny_round_mosaic.py --size 1024 --seed 7 --preset salt_pepper --out textures/penny_round_mosaic
python penny_round_mosaic.py --width 512 --height 256 --set columns=40 --orm --out maps
```

`--orm` also writes `penny_round_mosaic_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import penny_round_mosaic

maps = penny_round_mosaic.generate(512, 512, seed=3, preset="salt_pepper")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 18.4 s (9.5 s to compute, 8.9 s to write the PNG files) with a peak of about 551 MB; 256 x 256 takes about 1.12 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/penny_round_mosaic/` of your project (for example `python penny_round_mosaic.py --size 1024 --out path/to/project/baltor/textures/penny_round_mosaic`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.2). Change `uv1_scale` to repeat the tile.

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

Rounds are discs with a bullnose edge and a domed face; mesh-backed sheet seams, cut rounds at walls and glaze crazing are not modelled. In hexagonal packing the even row count squashes the lattice by about 1 percent for most column counts, more for very few columns. The colour rules are random or noise-driven, not designed motifs. Occlusion is a blurred-height estimate, not ray traced.
