# Halftone print screens: CMYK, comic dots, newsprint, duotone

A four-colour magazine print of a vivid poster, comic tints in large dots with solid black outlines on yellowed newsprint, a black-only newspaper photograph at 45 degrees, or a two-ink fluorescent duotone with loose registration. The design is separated into ink coverages: cyan, magenta and yellow from colour with black from their common part, or one darkness channel for single-ink prints.

Each ink is screened on its own rotated square lattice whose vector (p, q) is a pair of whole numbers, so the angle is close to the classic one and the screen still repeats exactly across the tile. A pixel is inked where the coverage exceeds a round-dot spot function, the share of a lattice cell nearer its centre than the pixel, so dots grow as circles and merge into a checkerboard past half coverage. Inks multiply over the paper, screens are nudged apart by `misregister`, and the paper carries fibres and patchy yellowing.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `halftone_print_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.95 |
| `normal` | `halftone_print_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `halftone_print_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `halftone_print_height.png` | 1 | linear | white is high |
| `ao` | `halftone_print_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Four-colour magazine print of a vivid poster at classic screen angles.
- `comic_dots`: Comic print: flat dot tints in large dots with solid black outlines on newsprint.
- `newsprint_mono`: Black-only newspaper photograph at 45 degrees on grey, aged paper.
- `riso_duotone`: Two fluorescent inks, pink and teal, coarse dots and loose registration.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `lines` | int | 40 | 8 to 128 | Screen lines (dot rows) across the tile. |
| `design_scale` | int | 2 | 1 to 6 | Features of the printed design across the tile. |
| `misregister` | float | 0.3 | 0 to 1 | Offset between the ink screens, as on a loose press. |
| `dot_gain` | float | 0.15 | 0 to 0.5 | Dots printing larger than their coverage, as ink spreads in the paper. |
| `yellowing` | float | 0.15 | 0 to 1 | Age yellowing of the paper in patches. |
| `fibres` | float | 0.4 | 0 to 1 | Visible paper fibres in colour and relief. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`halftone_print.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python halftone_print.py --size 1024 --seed 7 --preset comic_dots --out textures/halftone_print
python halftone_print.py --width 512 --height 256 --set lines=128 --orm --out maps
```

`--orm` also writes `halftone_print_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import halftone_print

maps = halftone_print.generate(512, 512, seed=3, preset="comic_dots")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 42.1 s (29.2 s to compute, 12.9 s to write the PNG files) with a peak of about 807 MB; 256 x 256 takes about 2.5 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/halftone_print/` of your project (for example `python halftone_print.py --size 1024 --out path/to/project/baltor/textures/halftone_print`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.5) and the height map through a Displacement node (scale 0.001, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Amplitude-modulated round dots only: no stochastic, line or elliptical screens. Screen angles are rounded to whole-number lattice vectors so the screen repeats, which moves them by up to a few degrees from the nominal angle at low line counts. The separation is a simple grey-component replacement without colour management or ink limits, inks multiply as ideal transparent filters, and dot gain is a curve rather than ink spreading. The printed design is procedural noise, not artwork. Fine screens alias below about four pixels per dot row.
