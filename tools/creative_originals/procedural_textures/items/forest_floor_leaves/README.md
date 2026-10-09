# Forest floor leaf litter

Autumn litter, dry brown oak leaves, wet dark decaying leaves or fresh red maple leaves. Leaves are stamped one after another with a z-buffer, each lying a little higher than the leaves under it, so the litter stacks.

A leaf outline is ovate or lobed, with a stem, a midrib, side veins and a darker rim, and a curl that lifts its edges. Each leaf takes an autumn colour and a decay level; twigs are thin capsules over the dark soil.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `forest_floor_leaves_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.85 |
| `normal` | `forest_floor_leaves_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `forest_floor_leaves_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.35 to 1 |
| `height` | `forest_floor_leaves_height.png` | 1 | linear | white is high |
| `ao` | `forest_floor_leaves_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Autumn litter of yellow, orange and brown leaves over soil.
- `oak_brown`: Dry brown oak leaves, mostly lobed.
- `wet_dark`: Wet, dark, decaying leaves pressed flat.
- `maple_red`: Fresh red and orange leaves, sparse over soil.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `leaves` | int | 190 | 20 to 1500 | Number of leaves on the tile. |
| `leaf_size` | float | 0.065 | 0.015 to 0.15 | Average leaf length (half extent) in texture units. |
| `lobed` | float | 0.3 | 0 to 1 | Share of lobed (oak-like) leaves; the rest are ovate. |
| `curl` | float | 0.5 | 0 to 1 | How much leaf edges lift. |
| `decay` | float | 0.3 | 0 to 1 | Share of dark, decaying leaves. |
| `twigs` | int | 10 | 0 to 60 | Number of twigs on the tile. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`forest_floor_leaves.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python forest_floor_leaves.py --size 1024 --seed 7 --preset oak_brown --out textures/forest_floor_leaves
python forest_floor_leaves.py --width 512 --height 256 --set leaves=1500 --orm --out maps
```

`--orm` also writes `forest_floor_leaves_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import forest_floor_leaves

maps = forest_floor_leaves.generate(512, 512, seed=3, preset="oak_brown")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17.3 s (7.6 s to compute, 9.7 s to write the PNG files) with a peak of about 508 MB; 256 x 256 takes about 1.19 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/forest_floor_leaves/` of your project (for example `python forest_floor_leaves.py --size 1024 --out path/to/project/baltor/textures/forest_floor_leaves`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.015, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Leaves are flat stamped outlines (ovate or lobed) with height-map curl; they do not fold or cast real shadows. Leaf shapes are generic, not species-accurate. Occlusion is a blurred-height estimate.
