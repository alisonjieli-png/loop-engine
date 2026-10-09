# Printed circuit board

A green board with gold pads and red LEDs, a dense blue board with tin pads, matte black with gold, or a dark board whose cyan data lines glow. Chips are placed first as dark rectangles with metal pins along two or four sides; traces leave from the pins and wander on a routing grid, turning only by multiples of 45 degrees, and end in vias, copper rings with a drilled hole.

Traces sit raised under the solder mask, which tints them lighter; exposed pads and pins are metal. Silkscreen draws small marks, indicator LEDs glow in the emissive map, and every element wraps around the tile edges.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `circuit_board_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `circuit_board_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `circuit_board_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.12 to 1 |
| `metallic` | `circuit_board_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `circuit_board_height.png` | 1 | linear | white is high |
| `ao` | `circuit_board_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `circuit_board_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Green solder mask with gold pads and red LEDs.
- `blue_dense`: Blue mask with dense fine traces and tin pads.
- `black_matte`: Matte black mask with gold traces and white LEDs.
- `glowing_traces`: Dark board with glowing cyan data lines.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `chips` | int | 3 | 0 to 10 | Chip packages on the tile. |
| `traces` | int | 40 | 4 to 160 | Traces routed across the board. |
| `grid` | int | 64 | 24 to 160 | Routing grid steps across the tile (higher gives finer traces). |
| `leds` | int | 4 | 1 to 30 | Glowing indicator LEDs. |
| `silkscreen` | float | 0.7 | 0 to 1 | Visibility of the white silkscreen outlines and marks. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and lights in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`circuit_board.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python circuit_board.py --size 1024 --seed 7 --preset blue_dense --out textures/circuit_board
python circuit_board.py --width 512 --height 256 --set chips=10 --orm --out maps
```

`--orm` also writes `circuit_board_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import circuit_board

maps = circuit_board.generate(512, 512, seed=3, preset="blue_dense")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 16.9 s (6.9 s to compute, 10 s to write the PNG files) with a peak of about 703 MB; 256 x 256 takes about 1.24 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/circuit_board/` of your project (for example `python circuit_board.py --size 1024 --out path/to/project/baltor/textures/circuit_board`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

## Limits

Traces are random routes on a grid, not a real netlist, and they may cross. Chips, LEDs and silkscreen are simplified shapes without text. The glowing-trace preset is stylized. The relief is shallow and carried mainly by the normal map. Occlusion is a blurred-height estimate, not ray traced.
