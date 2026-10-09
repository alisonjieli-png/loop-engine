# Cast concrete with formwork marks

Smooth cast concrete, board-formed concrete, architectural panels with tie holes, weathered concrete or a ground and polished floor. The cement face is a soft mottled grey with fine sand grain, and bug holes are small round pits.

`formwork` picks the imprint: none, horizontal boards with wood grain pressed in and a lip at every joint, or plywood panels with seams and a grid of tie holes. Water stains run down from joints and holes, wrapping across the tile edge. `aggregate` exposes pebbles and `polish` grinds the surface smooth.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `concrete_cast_albedo.png` | 3 | sRGB | glTF base colour, values 0.04 to 0.85 |
| `normal` | `concrete_cast_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `concrete_cast_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `height` | `concrete_cast_height.png` | 1 | linear | white is high |
| `ao` | `concrete_cast_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Smooth cast concrete with soft mottling and scattered bug holes.
- `board_formed`: Board-formed concrete showing wood grain and board joints.
- `tie_hole_panels`: Architectural panels with seams and tie holes.
- `weathered`: Old dark concrete with heavy stains and exposed grit.
- `polished_floor`: Ground and polished floor with exposed aggregate.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `formwork` | int | 0 | 0 to 2 | Formwork imprint: 0 smooth, 1 horizontal boards, 2 plywood panels with tie holes. |
| `panels` | int | 2 | 1 to 12 | Boards (formwork 1) or panel rows and columns (formwork 2) across the tile. |
| `bug_holes` | float | 0.4 | 0 to 1 | Density of small air-void pits. |
| `mottling` | float | 0.5 | 0 to 1 | Strength of the cloudy tone variation. |
| `stains` | float | 0.3 | 0 to 1 | Water stains running down from joints. |
| `aggregate` | float | 0 | 0 to 1 | Exposed aggregate: pebbles showing through the cement. |
| `polish` | float | 0 | 0 to 1 | Ground and polished finish (0 as cast, 1 polished floor). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`concrete_cast.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python concrete_cast.py --size 1024 --seed 7 --preset board_formed --out textures/concrete_cast
python concrete_cast.py --width 512 --height 256 --set formwork=2 --orm --out maps
```

`--orm` also writes `concrete_cast_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import concrete_cast

maps = concrete_cast.generate(512, 512, seed=3, preset="board_formed")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17.3 s (8.9 s to compute, 8.4 s to write the PNG files) with a peak of about 692 MB; 256 x 256 takes about 1.25 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/concrete_cast/` of your project (for example `python concrete_cast.py --size 1024 --out path/to/project/baltor/textures/concrete_cast`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Formwork marks are idealized: boards are horizontal and panels square, with four tie holes per panel. Stains always run toward the bottom of the tile. Aggregate stones are Voronoi cells. Occlusion is a blurred-height estimate.
