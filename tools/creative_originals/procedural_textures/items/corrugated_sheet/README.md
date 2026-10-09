# Corrugated sheet metal

Galvanized sine-wave sheet, faded barn red, a rusty shack wall or clean blue box-profile cladding. The profile runs across the tile with a whole number of ribs, so the sheet repeats; `profile` picks a sine wave or a trapezoidal box rib, and height follows it.

Screw heads with washers sit on the crests in evenly spaced rows (`screw_rows`). Rust streaks run down from the screws and from rusty patches: every column is swept downward with a fading trail, twice around so the trail wraps. Dirt gathers in the valleys. Galvanized sheet is metal; paint is a dielectric that chips through to it.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `corrugated_sheet_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `corrugated_sheet_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `corrugated_sheet_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `metallic` | `corrugated_sheet_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `corrugated_sheet_height.png` | 1 | linear | white is high |
| `ao` | `corrugated_sheet_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Galvanized sine-wave sheet with light dirt.
- `barn_red`: Red painted sheet with faded paint and rust runs.
- `rusty_shack`: Old sheet with heavy rust streaks.
- `box_profile_blue`: Blue painted box-profile cladding, clean.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `ribs` | int | 6 | 2 to 24 | Corrugations across the tile. |
| `profile` | int | 0 | 0 to 1 | Rib shape: 0 sine wave, 1 trapezoidal box rib. |
| `screw_rows` | int | 1 | 0 to 4 | Rows of screws across the tile (0 for none). |
| `paint` | float | 0 | 0 to 1 | Paint coverage (0 bare galvanized metal, 1 painted). |
| `rust` | float | 0.2 | 0 to 1 | Rust patches and the streaks below them. |
| `dirt` | float | 0.3 | 0 to 1 | Dirt in the valleys. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`corrugated_sheet.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python corrugated_sheet.py --size 1024 --seed 7 --preset barn_red --out textures/corrugated_sheet
python corrugated_sheet.py --width 512 --height 256 --set ribs=24 --orm --out maps
```

`--orm` also writes `corrugated_sheet_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import corrugated_sheet

maps = corrugated_sheet.generate(512, 512, seed=3, preset="barn_red")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 22.2 s (14.4 s to compute, 7.9 s to write the PNG files) with a peak of about 735 MB; 256 x 256 takes about 1.37 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/corrugated_sheet/` of your project (for example `python corrugated_sheet.py --size 1024 --out path/to/project/baltor/textures/corrugated_sheet`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.02, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Corrugations run down the tile (vertical ribs); rotate the UVs for horizontal cladding. The profile is a height map, so the wavy silhouette at a sheet's edge needs geometry. Streaks always run toward the bottom of the tile. Occlusion is a blurred-height estimate, not ray traced.
