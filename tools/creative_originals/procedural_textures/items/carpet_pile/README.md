# Carpet pile seen from above

A beige cut-pile plush, grey commercial loop pile, oatmeal berber with dark flecks, a cream shag rug or deep red velvet plush. Tufts sit on a jittered grid with whole numbers of tufts across and down, so the carpet tiles.

`pile` chooses the construction: cut-pile tufts show the twisted plies as a spiral, loops run in rows with diagonal ply grooves, berber uses fat nubby loops, and shag lays long bent strands over a short base pile. `tufts` sets the gauge, `tuft_size` how much backing shows, `flecks` the share of tufts with a fleck colour, and `shading` the light and dark patches of pile lying in different directions.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `carpet_pile_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `carpet_pile_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `carpet_pile_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.6 to 1 |
| `height` | `carpet_pile_height.png` | 1 | linear | white is high |
| `ao` | `carpet_pile_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Beige cut-pile plush carpet with soft shading.
- `grey_loop`: Grey commercial loop pile in tight rows.
- `berber_oat`: Oatmeal berber: fat nubby loops with dark flecks.
- `shag_cream`: Cream shag rug: long tangled strands over a short pile.
- `red_plush`: Deep red velvet plush with strong pile shading.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pile` | int | 0 | 0 to 3 | 0 cut pile (tuft tips), 1 loop pile in rows, 2 berber (fat flecked loops), 3 shag (long strands over a short pile). |
| `tufts` | int | 44 | 12 to 96 | Tufts (or loops) across the tile width; the grid is square, so as many rows run down the tile. |
| `tuft_size` | float | 0.85 | 0.5 to 1.2 | Tuft or loop thickness relative to the tuft spacing; low values show the backing. |
| `twist` | float | 0.6 | 0 to 1 | Visibility of the twisted plies in each tuft or loop. |
| `flecks` | float | 0 | 0 to 1 | Share of tufts in the fleck colour, as in berber or tweed carpets. |
| `shading` | float | 0.4 | 0 to 1 | Light and dark patches of pile lying in different directions. |
| `shag_length` | float | 0.07 | 0.02 to 0.14 | Length of the long shag strands in texture units (pile 3 only). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`carpet_pile.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python carpet_pile.py --size 1024 --seed 7 --preset grey_loop --out textures/carpet_pile
python carpet_pile.py --width 512 --height 256 --set pile=3 --orm --out maps
```

`--orm` also writes `carpet_pile_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import carpet_pile

maps = carpet_pile.generate(512, 512, seed=3, preset="grey_loop")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17.9 s (9.5 s to compute, 8.4 s to write the PNG files) with a peak of about 520 MB; 256 x 256 takes about 1.2 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/carpet_pile/` of your project (for example `python carpet_pile.py --size 1024 --out path/to/project/baltor/textures/carpet_pile`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.008, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Seen from straight above: tufts are domes and loops are capsules on a jittered square grid, not modelled yarn; pile depth shows only through height, normals and occlusion. Shag strands are bent two-segment strokes painted with a z-buffer, so very long strands look stiff. Pile shading is noise, not a record of footprints or a vacuum pattern. Patterned rugs, borders and fringes are out of scope. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic.
