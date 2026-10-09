# Bamboo poles and split slats

Dried golden poles, living green culms with pale waxy node bands, black bamboo, a split-slat mat or spotted tortoiseshell bamboo. Pole widths vary but are scaled to fill the tile width exactly, and each pole has a whole number of nodes down the tile, so the bamboo tiles in both directions.

`style` chooses round culms or flatter split slats, `poles` and `width_variation` the layout, `nodes` and `node_ridge` the nodes, each with a sheath scar below and a wax band above. `streaks` adds fibre streaks and tone along the culms, `spots` dark mottles, and `gap` the shadow between poles.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `bamboo_poles_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `bamboo_poles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `bamboo_poles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.2 to 1 |
| `height` | `bamboo_poles_height.png` | 1 | linear | white is high |
| `ao` | `bamboo_poles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Dried golden bamboo poles, as in a fence or screen.
- `green_fresh`: Living green culms with pale waxy node bands.
- `black_bamboo`: Black bamboo: dark purple-black culms with lighter nodes.
- `split_mat`: Split bamboo slats in a mat or blind, nodes staggered.
- `spotted_brown`: Spotted tortoiseshell bamboo with dark mottles.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `style` | int | 0 | 0 to 1 | 0 round culms side by side, 1 split slats (flatter, narrower strips). |
| `poles` | int | 6 | 2 to 40 | Poles or slats across the tile. |
| `width_variation` | float | 0.3 | 0 to 0.6 | Spread of pole widths. |
| `nodes` | int | 2 | 1 to 6 | Nodes per pole down the tile. |
| `node_ridge` | float | 0.6 | 0 to 1 | How strongly each node swells into a ridge. |
| `streaks` | float | 0.5 | 0 to 1 | Fibre streaks and tone along the culms. |
| `spots` | float | 0 | 0 to 1 | Dark mottled spots, as on spotted (tortoiseshell) bamboo. |
| `gap` | float | 0.05 | 0 to 0.3 | Dark gap between neighbouring poles, as a share of the pole width. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`bamboo_poles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python bamboo_poles.py --size 1024 --seed 7 --preset green_fresh --out textures/bamboo_poles
python bamboo_poles.py --width 512 --height 256 --set style=1 --orm --out maps
```

`--orm` also writes `bamboo_poles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import bamboo_poles

maps = bamboo_poles.generate(512, 512, seed=3, preset="green_fresh")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 13.5 s (7.2 s to compute, 6.3 s to write the PNG files) with a peak of about 556 MB; 256 x 256 takes about 1.08 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/bamboo_poles/` of your project (for example `python bamboo_poles.py --size 1024 --out path/to/project/baltor/textures/bamboo_poles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Culms are straight cylinders in a height field running down the tile, all lying in one plane; there is no taper, bend, branch, leaf, cut end or lashing. Node positions are jittered per pole, and pole widths vary but always fill the tile width exactly. The cylindrical shading is partly in the albedo as well as in the normal map. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic.
