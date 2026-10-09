# Breeze block screen wall with see-through openings

White painted blocks with a large circle and four small ones, cream quatrefoils, raw grey diamond blocks, terracotta flowers or pastel blocks with nine square holes. `blocks_across` square blocks sit in a stacked grid with mortar joints of `joint_width`, so the screen repeats in both directions.

Inside each block's solid rim (`frame`) an opening motif is cut from a signed distance in block coordinates, sized by `opening_scale`. The albedo's alpha is 0 in the openings and 1 on concrete and mortar, anti-aliased over a pixel, so the material renders with an alpha scissor. The concrete darkens toward the openings where the block's inner walls would show, rounds over `bevel`, and `weathering` adds stains and rain streaks.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `breeze_block_screen_albedo.png` | 4 | sRGB | glTF base colour, values 0.03 to 0.92 |
| `normal` | `breeze_block_screen_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `breeze_block_screen_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.5 to 1 |
| `height` | `breeze_block_screen_height.png` | 1 | linear | white is high |
| `ao` | `breeze_block_screen_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White painted blocks with a large circle and four small ones, mid-century style.
- `quatrefoil_cream`: Cream concrete quatrefoil blocks, three per side.
- `raw_diamond`: Raw grey concrete diamond blocks with pores and rain streaks.
- `terracotta_flower`: Terracotta clay flower blocks, butted with thin joints.
- `pastel_grille`: Pastel green blocks with nine square holes each.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `motif` | int | 0 | 0 to 4 | Opening cut in each block: 0 a circle with four small corner circles, 1 a quatrefoil, 2 a diamond with four corner triangles, 3 a four-petal flower around a solid centre, 4 a grille of nine square holes. |
| `blocks_across` | int | 2 | 1 to 6 | Blocks across the tile width (and height). |
| `frame` | float | 0.08 | 0.03 to 0.2 | Solid rim between the block edge and its openings, in block widths. |
| `opening_scale` | float | 0.9 | 0.5 to 1 | Size of the opening motif within the rim. |
| `joint_width` | float | 0.025 | 0 to 0.06 | Mortar joint between blocks in block widths; 0 butts the blocks together. |
| `bevel` | float | 0.015 | 0.004 to 0.05 | Rounded edge of the concrete around openings and joints, in block widths. |
| `weathering` | float | 0.3 | 0 to 1 | Stains, streaks and grime on the concrete. |
| `colour_variation` | float | 0.3 | 0 to 1 | Spread of tone between blocks. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`breeze_block_screen.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python breeze_block_screen.py --size 1024 --seed 7 --preset quatrefoil_cream --out textures/breeze_block_screen
python breeze_block_screen.py --width 512 --height 256 --set motif=4 --orm --out maps
```

`--orm` also writes `breeze_block_screen_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import breeze_block_screen

maps = breeze_block_screen.generate(512, 512, seed=3, preset="quatrefoil_cream")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 24.1 s (14 s to compute, 10.2 s to write the PNG files) with a peak of about 634 MB; 256 x 256 takes about 1.69 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/breeze_block_screen/` of your project (for example `python breeze_block_screen.py --size 1024 --out path/to/project/baltor/textures/breeze_block_screen`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses an alpha scissor at 0.5.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `alphaTest: 0.5`.

The openings are cut with an alpha scissor at 0.5 and the Godot template draws both faces (cull disabled), so the screen reads from either side of a single plane. For true depth in close views, extrude the blocks as geometry and keep these maps for the faces.

## Limits

The openings are alpha cut-outs on a flat card: the block depth is only suggested by darkening near the openings and the height map, so the see-through view does not shift with the viewing angle as real block walls do. Blocks are stacked in a square grid; running bond and half blocks are out of scope. Motifs are fixed signed-distance shapes, not catalogue designs. Occlusion is a blurred-height estimate, not ray traced.
