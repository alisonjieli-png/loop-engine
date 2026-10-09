# Ashlar masonry in coursed or broken bond

Cream limestone in coursed ashlar, grey granite in broken ashlar with rock-faced centres, chiselled sandstone with bedding streaks, or pale bush-hammered limestone. The tile is a grid of `courses` rows and 32 narrow columns; blocks of about `block_length` fill each row from a random offset, and in broken ashlar (`layout` 1) rows pair up into segments that are either one tall block or two independently jointed rows, so every layout repeats across both edges.

A block's face follows `face_style`: rubbed smooth with faint chisel lines, a drafted margin `margin` wide around a rock-faced centre that stands proud by `relief`, or bush-hammered stippling. Arrises are eroded and sooted by `weathering`, joints sit back by `joint_depth`, and each block takes its own colour from a hash.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `ashlar_masonry_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.9 |
| `normal` | `ashlar_masonry_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `ashlar_masonry_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.35 to 1 |
| `height` | `ashlar_masonry_height.png` | 1 | linear | white is high |
| `ao` | `ashlar_masonry_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Cream limestone in coursed ashlar, rubbed faces and thin joints.
- `rockfaced_granite`: Grey granite in broken ashlar with drafted margins and rock-faced centres.
- `sandstone_tooled`: Warm sandstone courses with chiselled faces and bedding streaks.
- `bush_hammered`: Pale limestone broken ashlar with stippled bush-hammered faces.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `layout` | int | 0 | 0 to 1 | 0 coursed ashlar (every block one course high, courses of varying height), 1 broken ashlar (blocks one to three equal rows high, joints broken in both directions). |
| `courses` | int | 5 | 2 to 14 | Rows of blocks across the tile height. |
| `block_length` | float | 0.3 | 0.12 to 0.7 | Mean block length in tile widths; each block varies by about 40 percent. |
| `joint_width` | float | 0.006 | 0.002 to 0.025 | Mortar joint width in texture units. |
| `joint_depth` | float | 0.4 | 0 to 1 | How far the mortar sits behind the faces. |
| `face_style` | int | 0 | 0 to 2 | 0 rubbed smooth with faint tool lines, 1 drafted margin around a rock-faced centre, 2 bush-hammered stippling. |
| `margin` | float | 0.018 | 0.004 to 0.05 | Width of the drafted margin around rock-faced centres, in texture units. |
| `relief` | float | 0.6 | 0 to 1 | How far rock-faced centres stand proud and how rough they are. |
| `tooling` | float | 0.4 | 0 to 1 | Depth of chisel lines on margins and smooth faces. |
| `weathering` | float | 0.3 | 0 to 1 | Eroded arrises, soot and streaks. |
| `colour_variation` | float | 0.5 | 0 to 1 | Spread of colour between blocks. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`ashlar_masonry.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python ashlar_masonry.py --size 1024 --seed 7 --preset rockfaced_granite --out textures/ashlar_masonry
python ashlar_masonry.py --width 512 --height 256 --set layout=1 --orm --out maps
```

`--orm` also writes `ashlar_masonry_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import ashlar_masonry

maps = ashlar_masonry.generate(512, 512, seed=3, preset="rockfaced_granite")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 21 s (10.7 s to compute, 10.4 s to write the PNG files) with a peak of about 639 MB; 256 x 256 takes about 1.72 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/ashlar_masonry/` of your project (for example `python ashlar_masonry.py --size 1024 --out path/to/project/baltor/textures/ashlar_masonry`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Blocks are rectangles on a 32-column grid, so block ends fall on multiples of 1/32 of the tile width; broken ashlar mixes one- and two-row blocks only. Tool lines, rock faces, stippling and weathering are noise and wave approximations, not carved geometry. Mineral speckle is a per-pixel pick, so it shimmers at small sizes. Occlusion is a blurred-height estimate, not ray traced.
