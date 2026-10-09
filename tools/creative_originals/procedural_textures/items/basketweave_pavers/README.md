# Basket weave brick and concrete pavers

Red clay pavers in two-paver basket weave, charcoal concrete in threes, old mossy brick or buff patio pavers. The tile is a checkerboard of `2 * repeats` squares per side; each square holds `bricks_per_square` pavers side by side, horizontal in one colour of the checkerboard and vertical in the other, so the pattern repeats in both directions.

Each paver's distance to its own sides shapes a top rounded by `edge_wear` above sand that fills the joints to `joint_fill`. A hash per paver gives its colour, a tilt from `settling` and darker fired ends and blotches from `flashing`; `moss` grows in the joints and creeps onto worn edges.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `basketweave_pavers_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.9 |
| `normal` | `basketweave_pavers_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `basketweave_pavers_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `basketweave_pavers_height.png` | 1 | linear | white is high |
| `ao` | `basketweave_pavers_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Red clay pavers in two-paver basket weave with light sand joints.
- `charcoal_concrete`: Charcoal concrete pavers in three-paver basket weave, crisp chamfers.
- `weathered_moss`: Old brown brick pavers, worn round, settled, with moss in the joints.
- `buff_patio`: Buff and tan clay pavers with grey sand and light flashing.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `bricks_per_square` | int | 2 | 2 to 4 | Pavers side by side in each square; the paver length is this many paver widths. |
| `repeats` | int | 2 | 1 to 6 | Pairs of checkerboard squares across the tile. |
| `joint_width` | float | 0.08 | 0.02 to 0.25 | Joint width in paver widths. |
| `joint_fill` | float | 0.55 | 0 to 0.95 | Height of the sand in the joints relative to the paver tops. |
| `edge_wear` | float | 0.35 | 0 to 1 | Rounding and chipping of the paver edges from traffic. |
| `flashing` | float | 0.4 | 0 to 1 | Darker fired ends and blotches on clay pavers. |
| `settling` | float | 0.3 | 0 to 1 | Uneven paver heights and tilts from a settled bed. |
| `moss` | float | 0 | 0 to 1 | Moss and dark dirt growing in the joints. |
| `colour_variation` | float | 0.55 | 0 to 1 | Spread of colour between pavers. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`basketweave_pavers.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python basketweave_pavers.py --size 1024 --seed 7 --preset charcoal_concrete --out textures/basketweave_pavers
python basketweave_pavers.py --width 512 --height 256 --set bricks_per_square=4 --orm --out maps
```

`--orm` also writes `basketweave_pavers_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import basketweave_pavers

maps = basketweave_pavers.generate(512, 512, seed=3, preset="charcoal_concrete")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 20.3 s (10.7 s to compute, 9.7 s to write the PNG files) with a peak of about 640 MB; 256 x 256 takes about 1.46 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/basketweave_pavers/` of your project (for example `python basketweave_pavers.py --size 1024 --out path/to/project/baltor/textures/basketweave_pavers`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

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

Pavers are rectangles whose length equals the square side, so the layout is the plain basket weave only; half basket and diagonal variants, borders and cut pavers are out of scope. Flashing, chips, settling and moss are noise-driven approximations. Colours are artistic, not measured. Occlusion is a blurred-height estimate, not ray traced.
