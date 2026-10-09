# Thatched roof of straw or water reed

Golden long-straw thatch, combed water reed, old grey thatch with moss, or new pale wheat straw. The slope runs down the tile from the ridge at the top, and the tile holds a whole number of courses, each overlapping the one below, so the roof tiles in both directions.

Every course is painted strand by strand: `style` lays long straws down the slope or shows the cut butts of combed reed. `courses`, `density` and `strand_width` set the layout, `raggedness` how uneven each course edge is, `weathering` greys the straw in patches, and `moss` grows in the shelter just below each course edge.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `straw_thatch_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `straw_thatch_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `straw_thatch_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.45 to 1 |
| `height` | `straw_thatch_height.png` | 1 | linear | white is high |
| `ao` | `straw_thatch_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Golden long-straw thatch with ragged course edges.
- `water_reed`: Combed water reed: dense cut butts, crisp courses.
- `weathered_grey`: Old grey thatch with moss under the course edges.
- `fresh_wheat`: New pale wheat straw, fine and even.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `style` | int | 0 | 0 to 1 | 0 long straw laid along the slope, 1 combed water reed showing the cut butts. |
| `courses` | int | 4 | 2 to 10 | Courses down the tile; each overlaps the one below. |
| `density` | float | 1 | 0.5 to 2 | Strands per course; 1 covers each course about three times over, so little shadow shows. |
| `strand_width` | float | 0.0032 | 0.0015 to 0.007 | Straw or reed thickness in texture units. |
| `raggedness` | float | 0.5 | 0 to 1 | How uneven the lower edge of each course is. |
| `weathering` | float | 0.2 | 0 to 1 | Greying of the straw with age. |
| `moss` | float | 0 | 0 to 1 | Moss in the shelter below each course edge. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`straw_thatch.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python straw_thatch.py --size 1024 --seed 7 --preset water_reed --out textures/straw_thatch
python straw_thatch.py --width 512 --height 256 --set style=1 --orm --out maps
```

`--orm` also writes `straw_thatch_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import straw_thatch

maps = straw_thatch.generate(512, 512, seed=3, preset="water_reed")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 42.9 s (21.5 s to compute, 21.4 s to write the PNG files) with a peak of about 518 MB; 256 x 256 takes about 2.23 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/straw_thatch/` of your project (for example `python straw_thatch.py --size 1024 --out path/to/project/baltor/textures/straw_thatch`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Courses are straight horizontal bands of painted strokes; ridges, eaves, gables and decorative ridge patterns are out of scope. The slope runs down the tile (ridge at the top), so map V along the roof slope. Strands are straight capsules with a z-buffer, not bent fibres, and the moss is a tint with a slight lift, not modelled growth. Strand counts are fixed per course, so very thin strands at small sizes are drawn at least about a pixel wide. Occlusion is a blurred-height estimate.
