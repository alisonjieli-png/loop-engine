# Brick wall courses in four bonds

Red, buff, brown or glazed bricks laid in courses. The layout is computed in texture space from a bond pattern (brick lengths and an offset for each of two courses), so the wall repeats every two courses and tiles in both directions.

Each brick takes its colour, face height, slight tilt and roughness from a hash of its index. Mortar joints sit below the faces by `joint_depth`, edges are rounded over `bevel` and eroded by noise when `chipping` is above zero. Flemish bond darkens its headers, as burnt header ends often are.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `brick_courses_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.9 |
| `normal` | `brick_courses_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `brick_courses_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `height` | `brick_courses_height.png` | 1 | linear | white is high |
| `ao` | `brick_courses_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Red clay bricks in running bond with light grey mortar.
- `weathered`: Old dark bricks, chipped edges, deep joints, soot and white salt bloom.
- `flemish_buff`: Buff yellow bricks in Flemish bond with darker headers.
- `english_brown`: Brown bricks in English bond with dark mortar.
- `glazed_stack`: Glossy white glazed bricks in stack bond with thin flush joints.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `bond` | int | 0 | 0 to 3 | 0 running (stretchers offset by half a brick), 1 Flemish (headers and stretchers alternate in each course), 2 English (stretcher and header courses alternate), 3 stack (joints aligned). |
| `course_pairs` | int | 4 | 1 to 12 | Pairs of courses across the tile height; every bond repeats after two courses. |
| `bricks_per_course` | int | 3 | 1 to 10 | Stretchers per course across the tile width (Flemish: header and stretcher pairs). |
| `mortar_width` | float | 0.012 | 0.002 to 0.04 | Joint width in texture units (fractions of the tile width). |
| `joint_depth` | float | 0.5 | 0 to 1 | How far the mortar sits below the brick faces: 0 flush, 1 deeply raked. |
| `bevel` | float | 0.008 | 0.001 to 0.03 | Width of the rounded brick edge in texture units. |
| `chipping` | float | 0.3 | 0 to 1 | Broken and eroded brick edges, 0 crisp to 1 heavily damaged. |
| `colour_variation` | float | 0.5 | 0 to 1 | Spread of colour between bricks. |
| `grime` | float | 0.2 | 0 to 1 | Soot and dirt in the joints and on the faces. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`brick_courses.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python brick_courses.py --size 1024 --seed 7 --preset weathered --out textures/brick_courses
python brick_courses.py --width 512 --height 256 --set bond=3 --orm --out maps
```

`--orm` also writes `brick_courses_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import brick_courses

maps = brick_courses.generate(512, 512, seed=3, preset="weathered")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 16.1 s (8.8 s to compute, 7.3 s to write the PNG files) with a peak of about 655 MB; 256 x 256 takes about 1.2 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/brick_courses/` of your project (for example `python brick_courses.py --size 1024 --out path/to/project/baltor/textures/brick_courses`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 2). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.018, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Bricks are flat rectangles with rounded edges; there are no corner returns, cut bricks or openings. The bond repeats every two courses, so a tile shows an even number of courses. Salt bloom, soot and chips are noise-driven approximations. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic, not measured from real clay.
