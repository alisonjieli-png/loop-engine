# Clay roof tiles, barrel or pantile

Terracotta barrel tiles, even red pantiles, a faded Mediterranean roof or glossy green glazed tiles. Across the slope the tile repeats a curved profile `columns` times: a concave pan between half-round covers for barrel tiles, or one S-shaped piece for pantiles. Down the slope `courses` rows overlap, and each column of tiles is shifted a little by `misalignment`, so the roof repeats in both directions.

Each tile rises from where it slides under the course above to a nose resting on the course below, so every nose casts a step (`course_step`) and barrel covers show a dark cavity under their ends. Crowns are bleached lighter and channels darker; `dirt` washes streaks down the pans, `moss` settles under the noses, `lichen` adds orange and pale colonies and `glaze` turns matte clay into glossy glazed tiles.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `roof_tiles_clay_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `roof_tiles_clay_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `roof_tiles_clay_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.08 to 1 |
| `height` | `roof_tiles_clay_height.png` | 1 | linear | white is high |
| `ao` | `roof_tiles_clay_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Terracotta barrel tiles with half-round covers and a little lichen.
- `red_pantiles`: Even red pantiles in tight courses, recently laid.
- `aged_mediterranean`: Faded, mottled barrel tiles with heavy lichen, moss and streaks.
- `glazed_jade`: Glossy green glazed barrel tiles with narrow covers in many courses.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `profile` | int | 0 | 0 to 1 | 0 barrel tiles (concave pans with separate half-round covers over their joints), 1 pantiles (one S-shaped piece: a pan rising into a roll that laps the next pan). |
| `columns` | int | 5 | 2 to 14 | Profile repeats across the tile width (pan and cover pairs, or pantiles). |
| `courses` | int | 5 | 2 to 14 | Overlapping courses down the tile height. |
| `cover_width` | float | 0.42 | 0.25 to 0.55 | Share of each repeat taken by the convex cover or roll. |
| `curvature` | float | 0.7 | 0.1 to 1 | Depth of the curves across the slope. |
| `course_step` | float | 0.5 | 0 to 1 | Height of the step at each tile nose. |
| `misalignment` | float | 0.3 | 0 to 1 | Random offsets and tilts of individual tiles. |
| `lichen` | float | 0.25 | 0 to 1 | Orange and pale lichen spots. |
| `moss` | float | 0.1 | 0 to 1 | Moss in the pans under the noses. |
| `dirt` | float | 0.3 | 0 to 1 | Dark streaks washed down the pans. |
| `glaze` | float | 0 | 0 to 1 | 0 unglazed clay, 1 glossy glazed tiles. |
| `colour_variation` | float | 0.6 | 0 to 1 | Spread of colour between tiles. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`roof_tiles_clay.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python roof_tiles_clay.py --size 1024 --seed 7 --preset red_pantiles --out textures/roof_tiles_clay
python roof_tiles_clay.py --width 512 --height 256 --set profile=1 --orm --out maps
```

`--orm` also writes `roof_tiles_clay_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import roof_tiles_clay

maps = roof_tiles_clay.generate(512, 512, seed=3, preset="red_pantiles")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 29.3 s (16.5 s to compute, 12.8 s to write the PNG files) with a peak of about 687 MB; 256 x 256 takes about 2.05 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/roof_tiles_clay/` of your project (for example `python roof_tiles_clay.py --size 1024 --out path/to/project/baltor/textures/roof_tiles_clay`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 2.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.035, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The slope always runs down the tile height. Tiles are straight-sided curved profiles with no taper, ridge, hip, eaves or verge pieces, and the curvature lives in the height and normal maps only, so silhouettes stay flat without displacement. Crowns are tinted lighter and channels darker in the albedo as weathering, which reads as baked shading under strong grazing light. Lichen, moss and streaks are noise approximations. Occlusion is a blurred-height estimate, not ray traced.
