# Cobblestone paving from Voronoi cells

Grey granite cobbles, rounded river stones in sand, mossy old cobbles, dark basalt setts or warm sandstone. Each stone is one cell of a jittered Voronoi diagram on the torus, so the pattern tiles. The distance to the cell border (the bisector with the nearest neighbour) shapes a domed top that rises over `roundness`; `corner_rounding` trims each stone toward a disc around its feature point, and noise roughens the outline by `irregularity`.

Each stone takes its colour, crown height and roughness from a hash of its cell. Soil or sand fills the joints up to `gap_fill`, stone crowns are polished by `wear`, and `moss` grows in the joints and creeps onto low stone edges.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `cobblestone_voronoi_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.85 |
| `normal` | `cobblestone_voronoi_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `cobblestone_voronoi_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.25 to 1 |
| `height` | `cobblestone_voronoi_height.png` | 1 | linear | white is high |
| `ao` | `cobblestone_voronoi_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey granite cobbles with dark soil joints.
- `river_rounded`: Rounded river stones in warm sand, deep joints.
- `mossy`: Old irregular cobbles with moss in the joints.
- `basalt_setts`: Dark basalt setts in a near-square grid with flat tops.
- `sandstone`: Warm sandstone cobbles with pale mortar-like sand.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `stones_across` | int | 7 | 3 to 16 | Stones across the tile (cells of the Voronoi grid per side). |
| `jitter` | float | 0.75 | 0 to 1 | How far each stone's centre strays from a square grid: 0 square setts, 1 irregular cobbles. |
| `gap_width` | float | 0.08 | 0.01 to 0.3 | Joint width between stones, in stone widths. |
| `roundness` | float | 0.35 | 0.05 to 1 | How far in from the edge the dome rises, in stone widths: small values give flat tops. |
| `corner_rounding` | float | 0.6 | 0 to 1 | Rounds the stone corners: 0 keeps the Voronoi polygon, 1 trims each stone to a disc. |
| `irregularity` | float | 0.06 | 0 to 0.2 | Noise on the stone outlines, in stone widths. |
| `wear` | float | 0.5 | 0 to 1 | Polish of the stone tops from foot traffic (lower roughness on the crowns). |
| `gap_fill` | float | 0.45 | 0 to 0.9 | Height of the soil or sand in the joints relative to the stone crowns. |
| `moss` | float | 0 | 0 to 1 | Moss growing in the joints and creeping onto stone edges. |
| `colour_variation` | float | 0.6 | 0 to 1 | Spread of colour and brightness between stones. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`cobblestone_voronoi.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python cobblestone_voronoi.py --size 1024 --seed 7 --preset river_rounded --out textures/cobblestone_voronoi
python cobblestone_voronoi.py --width 512 --height 256 --set stones_across=16 --orm --out maps
```

`--orm` also writes `cobblestone_voronoi_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import cobblestone_voronoi

maps = cobblestone_voronoi.generate(512, 512, seed=3, preset="river_rounded")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 24.2 s (12.5 s to compute, 11.7 s to write the PNG files) with a peak of about 768 MB; 256 x 256 takes about 1.57 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/cobblestone_voronoi/` of your project (for example `python cobblestone_voronoi.py --size 1024 --out path/to/project/baltor/textures/cobblestone_voronoi`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 3). Change `uv1_scale` to repeat the tile.

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

Stones are Voronoi cells, optionally trimmed toward discs, so they read as cut setts or rounded cobbles rather than scanned stones. Stones do not overlap and have no undercut. With jitter near 1 a few feature points fall close together and give narrow stones. Moss and soil are noise masks. Occlusion is a blurred-height estimate.
