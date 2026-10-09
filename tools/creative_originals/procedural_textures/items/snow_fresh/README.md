# Snow surface

Fresh powder, wind-packed sastrugi, old crusted snow or deep rolling drifts. Fresh snow is a gentle swell of low-frequency noise with fine crystal grain. Glints are tiny stamps placed in texture space that are brighter and smoother than the snow around them.

Hollows take a cool blue tint, a cheap stand-in for light scattered inside the snowpack. `wind_ridges` carves sharp ridges, and `age` adds dirt specks, a glazed crust and melt pits.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `snow_fresh_albedo.png` | 3 | sRGB | glTF base colour, values 0.3 to 0.95 |
| `normal` | `snow_fresh_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `snow_fresh_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `height` | `snow_fresh_height.png` | 1 | linear | white is high |
| `ao` | `snow_fresh_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Fresh powder with soft drifts and glints.
- `sastrugi`: Wind-packed snow carved into sharp ridges.
- `old_crusted`: Old, dirty snow with an icy crust and melt pits.
- `drift_field`: Large rolling drifts in deep fresh snow under a cold blue sky.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `drift_scale` | int | 3 | 1 to 12 | Noise cells across the tile for the drifts (higher gives smaller drifts). |
| `drift_height` | float | 0.5 | 0 to 1 | Height of the soft drifts. |
| `wind_ridges` | float | 0 | 0 to 1 | Sharp wind-carved ridges (sastrugi). |
| `glints` | float | 0.5 | 0 to 1 | Density of sparkling crystal glints. |
| `age` | float | 0 | 0 to 1 | Old snow: dirt specks, glazed crust and melt pits. |
| `blue_tint` | float | 0.4 | 0 to 1 | Cool tint in the hollows. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`snow_fresh.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python snow_fresh.py --size 1024 --seed 7 --preset sastrugi --out textures/snow_fresh
python snow_fresh.py --width 512 --height 256 --set drift_scale=12 --orm --out maps
```

`--orm` also writes `snow_fresh_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import snow_fresh

maps = snow_fresh.generate(512, 512, seed=3, preset="sastrugi")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 33.5 s (10.7 s to compute, 22.8 s to write the PNG files) with a peak of about 664 MB; 256 x 256 takes about 1.9 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/snow_fresh/` of your project (for example `python snow_fresh.py --size 1024 --out path/to/project/baltor/textures/snow_fresh`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Light scattering inside snow is only suggested by a blue tint in the hollows; use a subsurface or translucency setting in the engine for real scattering. Glints are small bright, smooth spots in the maps, not view-dependent sparkle. Occlusion is a blurred-height estimate.
