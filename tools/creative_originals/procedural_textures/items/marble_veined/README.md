# Veined marble

White, Calacatta-like, black, green or red marble. Veins are the places where a stretched fractal noise field crosses zero: long curves that run mostly one way, branch now and then and close rarely. The field is warped by smooth noise and sheared by whole tiles to run diagonally, so the texture still repeats.

Each vein's width comes from the distance to the zero crossing (the field value divided by its gradient), so a vein keeps its width in texture space; slow noise swells and thins it along its length and fast noise roughens its edges. A second, finer field adds thin secondary veins and a soft cloud tints the stone. The surface is polished: the height map carries only slight vein recesses and pits, and roughness follows `polish`.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `marble_veined_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `marble_veined_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `marble_veined_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 0.8 |
| `height` | `marble_veined_height.png` | 1 | linear | white is high |
| `ao` | `marble_veined_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White stone with soft grey diagonal veins, polished.
- `calacatta`: Warm white stone with bold, widely spaced grey and gold veins.
- `nero`: Black stone with sharp white veins.
- `verde`: Dark green serpentine marble with pale meandering veins, honed.
- `rosso`: Red-brown marble with cream veins and strong clouds.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `vein_spacing` | int | 2 | 1 to 8 | Noise cells across the veins: higher values give more, closer veins. |
| `vein_direction` | int | 0 | 0 to 4 | Vein run: 0 falling diagonal, 1 rising diagonal, 2 horizontal, 3 vertical, 4 steep diagonal. |
| `vein_width` | float | 0.008 | 0.002 to 0.04 | Average width of the main veins in texture units. |
| `flow` | float | 0.06 | 0 to 0.2 | Domain warp in texture units: how much the veins meander. |
| `secondary_veins` | float | 0.5 | 0 to 1 | Strength of the thin secondary veins. |
| `cloudiness` | float | 0.5 | 0 to 1 | Soft tonal clouds in the stone between veins. |
| `polish` | float | 0.85 | 0 to 1 | Surface finish from honed (0, matte) to polished (1, glossy). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`marble_veined.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python marble_veined.py --size 1024 --seed 7 --preset calacatta --out textures/marble_veined
python marble_veined.py --width 512 --height 256 --set vein_spacing=8 --orm --out maps
```

`--orm` also writes `marble_veined_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import marble_veined

maps = marble_veined.generate(512, 512, seed=3, preset="calacatta")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 24.1 s (15.8 s to compute, 8.3 s to write the PNG files) with a peak of about 985 MB; 256 x 256 takes about 2.22 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/marble_veined/` of your project (for example `python marble_veined.py --size 1024 --out path/to/project/baltor/textures/marble_veined`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.6) and the height map through a Displacement node (scale 0.003, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Veins are zero crossings of warped anisotropic noise, an approximation of mineral-filled fractures, not a geological simulation; vein directions are limited to five whole-tile shears so the texture repeats. Relief is very shallow by design. Colours are artistic, not measured from named quarries. Occlusion is a blurred-height estimate.
