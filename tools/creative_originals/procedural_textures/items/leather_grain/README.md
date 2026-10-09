# Pebbled and suede leather

Black car-seat leather, tan saddle leather, coarse navy handbag leather, cracked oxblood club-chair leather or brushed tan suede. The grain is a cellular pattern on the torus, so the hide tiles in both directions, and every cell becomes a rounded pebble bordered by creases.

`grain_cells` sets the pebble size and `grain_depth` the crease depth; `fine_grain` adds small creases inside the pebbles and `pores` small pits. `wrinkles` lays long fold creases across the hide, `wear` lightens and polishes the high points in patches, `cracking` breaks an old finish into a network that shows the leather below, and `nap` hides the grain under suede fibres with brushed light and dark patches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `leather_grain_albedo.png` | 3 | sRGB | glTF base colour, values 0.015 to 0.9 |
| `normal` | `leather_grain_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `leather_grain_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.18 to 1 |
| `height` | `leather_grain_height.png` | 1 | linear | white is high |
| `ao` | `leather_grain_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Black car-seat leather: fine even pebble grain with a satin finish.
- `saddle_brown`: Smooth tan saddle leather: shallow grain, wrinkles and burnished wear.
- `pebbled_navy`: Navy handbag leather with a coarse, deep pebble grain.
- `aged_oxblood`: Oxblood club-chair leather with a cracked finish and worn patches.
- `suede_tan`: Tan suede: brushed nap with light and dark patches.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `grain_cells` | int | 26 | 6 to 64 | Pebbles across the tile width: low values give a coarse bag grain, high values a fine one. |
| `grain_depth` | float | 0.6 | 0 to 1 | How deep the creases between pebbles are. |
| `fine_grain` | float | 0.5 | 0 to 1 | Small creases inside the pebbles, at about 2.3 times the pebble frequency (dropped where they would be finer than two pixels). |
| `pores` | float | 0.35 | 0 to 1 | Density and depth of the small pores of the hide. |
| `wrinkles` | float | 0.25 | 0 to 1 | Long creases from folding and use. |
| `wear` | float | 0.2 | 0 to 1 | Burnished, lighter and glossier high points, in patches. |
| `cracking` | float | 0 | 0 to 1 | Cracks in an old surface finish, showing the darker leather below. |
| `nap` | float | 0 | 0 to 1 | Suede nap: fine fibres hide the grain and brushing leaves light and dark patches. |
| `gloss` | float | 0.4 | 0 to 1 | Shine of the finish: 0 matte, 1 polished. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`leather_grain.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python leather_grain.py --size 1024 --seed 7 --preset saddle_brown --out textures/leather_grain
python leather_grain.py --width 512 --height 256 --set grain_cells=64 --orm --out maps
```

`--orm` also writes `leather_grain_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import leather_grain

maps = leather_grain.generate(512, 512, seed=3, preset="saddle_brown")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 34.7 s (21.2 s to compute, 13.6 s to write the PNG files) with a peak of about 1090 MB; 256 x 256 takes about 2.73 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/leather_grain/` of your project (for example `python leather_grain.py --size 1024 --out path/to/project/baltor/textures/leather_grain`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

The grain is a warped cellular pattern with noise creases, a stylized stand-in for real hide structure; species-specific grains (ostrich, crocodile, snake) are out of scope. Wrinkles are noise crests, not simulated folds, and the suede nap is a fibre-noise and brushing-patch approximation without directional sheen. Wear and cracks are noise-driven and spread evenly rather than following seams or edges. Details finer than two pixels are dropped at small sizes. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic, not measured.
