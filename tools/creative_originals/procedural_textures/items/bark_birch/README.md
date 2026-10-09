# Birch bark

Paper birch, aged silver birch, salmon river birch or young smooth bark, with the trunk axis running down the tile. Lenticels are short horizontal dashes; branch scars are dark chevrons; dark fissured patches come from stretched noise broken up by finer noise and crossed by cracks.

Peeling strips are ragged horizontal bands where the tan inner bark shows, with a bright curled lip along the upper edge. Every mark wraps around the tile edges.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `bark_birch_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `bark_birch_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `bark_birch_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.4 to 1 |
| `height` | `bark_birch_height.png` | 1 | linear | white is high |
| `ao` | `bark_birch_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Paper birch: chalk-white bark with dark lenticels and a few scars.
- `silver_aged`: Older silver birch with large black fissured patches.
- `river_birch`: Salmon-tan river birch with heavy curling peel.
- `young_smooth`: Young smooth birch with fine, sparse lenticels and no scars.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `lenticels` | float | 0.5 | 0 to 1 | Density of the horizontal lenticel dashes. |
| `lenticel_length` | float | 0.05 | 0.01 to 0.15 | Average lenticel length in texture units. |
| `dark_patches` | float | 0.15 | 0 to 1 | Share of dark, fissured bark. |
| `branch_scars` | int | 2 | 0 to 8 | Dark chevron branch scars on the tile. |
| `peeling` | float | 0.3 | 0 to 1 | Strips of outer bark peeled off, showing the inner bark. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`bark_birch.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python bark_birch.py --size 1024 --seed 7 --preset silver_aged --out textures/bark_birch
python bark_birch.py --width 512 --height 256 --set lenticels=1 --orm --out maps
```

`--orm` also writes `bark_birch_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import bark_birch

maps = bark_birch.generate(512, 512, seed=3, preset="silver_aged")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.1 s (12.2 s to compute, 12.9 s to write the PNG files) with a peak of about 708 MB; 256 x 256 takes about 1.5 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/bark_birch/` of your project (for example `python bark_birch.py --size 1024 --out path/to/project/baltor/textures/bark_birch`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Marks are placed at random in texture space; real birch bark changes along the trunk, which a single tile cannot show. Peeling strips are flat bands with a raised lip, not separate geometry. Occlusion is a blurred-height estimate.
