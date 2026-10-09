# Painted metal with chips and scratches

Safety yellow, matte olive drab, glossy red enamel, worn machinery blue or a faded old tractor green. Three layers are stacked: a top coat, a grey primer and bare steel. A warped fractal decides where the paint has chipped; a pixel near the rim of a chip still shows primer and one deep inside shows steel, so every chip has the stepped edge of real flaking paint.

Scratches are thin strokes, mostly along one direction (`scratch_direction`), that cut through both coats. Exposed steel can rust, grime settles over everything in a soft layer, and the metallic map is 1 only where bare steel shows, so the paint stays a dielectric with its own gloss (`paint_gloss`).

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `painted_metal_scratched_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `painted_metal_scratched_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `painted_metal_scratched_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `painted_metal_scratched_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `painted_metal_scratched_height.png` | 1 | linear | white is high |
| `ao` | `painted_metal_scratched_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Safety yellow over grey primer with chips and scratches.
- `olive_drab`: Matte military olive drab, heavily scuffed.
- `glossy_red`: Glossy red enamel with a few fine scratches.
- `machinery_blue`: Worn blue machinery paint with oily grime.
- `old_tractor`: Faded green paint flaking off rusty steel.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `chipping` | float | 0.35 | 0 to 1 | Share of the paint chipped away. |
| `chip_scale` | int | 6 | 2 to 24 | Noise cells across the tile for the chips (higher gives smaller chips). |
| `scratches` | int | 40 | 0 to 300 | Number of scratches. |
| `scratch_direction` | float | 0.3 | 0 to 1 | How strongly scratches follow one direction (0 random, 1 parallel). |
| `rust` | float | 0.2 | 0 to 1 | Rust on the exposed metal. |
| `grime` | float | 0.3 | 0 to 1 | Dirt and dust over the paint. |
| `paint_gloss` | float | 0.5 | 0 to 1 | Gloss of the top coat (0 flat, 1 glossy enamel). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`painted_metal_scratched.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python painted_metal_scratched.py --size 1024 --seed 7 --preset olive_drab --out textures/painted_metal_scratched
python painted_metal_scratched.py --width 512 --height 256 --set chipping=1 --orm --out maps
```

`--orm` also writes `painted_metal_scratched_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import painted_metal_scratched

maps = painted_metal_scratched.generate(512, 512, seed=3, preset="olive_drab")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.2 s (12.9 s to compute, 12.3 s to write the PNG files) with a peak of about 769 MB; 256 x 256 takes about 1.6 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/painted_metal_scratched/` of your project (for example `python painted_metal_scratched.py --size 1024 --out path/to/project/baltor/textures/painted_metal_scratched`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Chips and scratches are placed by noise and random strokes, not by where a real object wears (edges, handles, contact points); combine the maps with an edge-wear mask from your tool for that. Scratches carry no burr or directional sheen. Rust is a colour and roughness layer without its own relief. Occlusion is a blurred-height estimate, not ray traced.
