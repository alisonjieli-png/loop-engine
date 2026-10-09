# Cork board, tiles and natural cork

A notice board with pin holes, a fine sealed cork floor tile, coarse black expanded cork insulation, or the golden mass of a natural wine stopper with dark lenticels. Every layer is periodic on the torus, so the cork tiles in both directions.

Agglomerated cork (`pattern` 0) mixes coarse granules with finer fragments (`fragments`), each with its own tone (`tone_variation`), and sinks the borders between granules into crevices (`gaps`). Natural cork (`pattern` 1) is one mass with lenticels. `pores` pits the surface, `pin_holes` punches holes with a raised rim, and `sealed` fills the pores, deepens the colour and adds gloss.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `cork_board_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `cork_board_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `cork_board_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.25 to 1 |
| `height` | `cork_board_height.png` | 1 | linear | white is high |
| `ao` | `cork_board_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Notice-board cork: mixed granules with pin holes.
- `floor_tile`: Fine sealed cork floor tile with a satin varnish.
- `expanded_dark`: Heat-expanded black cork insulation: coarse dark granules, deep gaps.
- `natural_stopper`: Natural cork as in a wine stopper: golden mass with dark lenticels.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 1 | 0 agglomerated granules (boards, tiles), 1 natural cork with lenticels (stoppers, bark slabs). |
| `granules` | int | 30 | 8 to 72 | Granules across the tile width (agglomerated cork). |
| `fragments` | float | 0.5 | 0 to 1 | Visibility of the finer fragments inside the granules. |
| `gaps` | float | 0.35 | 0 to 1 | Depth and darkness of the crevices between granules. |
| `pores` | float | 0.45 | 0 to 1 | Density of fine pores (and of lenticels in natural cork). |
| `pin_holes` | int | 12 | 0 to 60 | Pin holes punched into the tile. |
| `tone_variation` | float | 0.6 | 0 to 1 | Spread of colour between granules. |
| `sealed` | float | 0 | 0 to 1 | Varnish: fills pores, deepens the colour and adds gloss. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`cork_board.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python cork_board.py --size 1024 --seed 7 --preset floor_tile --out textures/cork_board
python cork_board.py --width 512 --height 256 --set pattern=1 --orm --out maps
```

`--orm` also writes `cork_board_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import cork_board

maps = cork_board.generate(512, 512, seed=3, preset="floor_tile")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 28.2 s (16.7 s to compute, 11.5 s to write the PNG files) with a peak of about 1074 MB; 256 x 256 takes about 1.53 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/cork_board/` of your project (for example `python cork_board.py --size 1024 --out path/to/project/baltor/textures/cork_board`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Granules are two warped cellular layers with per-cell tones, an approximation of pressed cork, and the lenticels of natural cork are thresholded stretched noise. Pin holes are round dark pits with a raised rim; no pins, paper or staples are drawn. The sealed finish is a colour and roughness change without a clear-coat layer. Details finer than two pixels are dropped at small sizes. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic.
