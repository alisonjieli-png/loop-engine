# Opus vermiculatum tesserae mosaic

A Roman stone mosaic with ochre and red roundels, a Byzantine gold smalti ground around blue and green motifs, teal rings around small white motifs, or large earth-toned stone tesserae. `motifs` discs of about `motif_size` are scattered over the tile with wrap-around spacing, so the mosaic repeats in both directions.

Each pixel takes the nearest motif by signed distance and lays tesserae in that motif's rings: ring k holds the points between k and k + 1 tessera sizes from the disc, cut into a whole number of tesserae so every ring closes. Rings inside fill the motif, `outline_rows` rings outline it and the rest form the background, whose rows from neighbouring motifs meet along irregular seams as in hand-laid mosaic. `irregularity` trims and tilts each tessera, `relief` sets it unevenly in the mortar and `gloss` runs from matte stone to glass.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `mosaic_tesserae_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `mosaic_tesserae_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `mosaic_tesserae_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `metallic` | `mosaic_tesserae_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `mosaic_tesserae_height.png` | 1 | linear | white is high |
| `ao` | `mosaic_tesserae_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Roman stone mosaic: cream background rows around ochre and red motifs with dark outlines.
- `gold_smalti`: Byzantine glass smalti: metallic gold background rows around blue and green motifs.
- `sea_rings`: Teal and blue rings rippling around small white motifs, no outline.
- `earth_stone`: Large matte stone tesserae in earth tones with wide joints.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `motifs` | int | 5 | 1 to 16 | Round motifs scattered over the tile. |
| `motif_size` | float | 0.09 | 0.03 to 0.2 | Mean motif radius in tile widths. |
| `tessera_size` | float | 0.02 | 0.008 to 0.05 | Side of one tessera in tile widths. |
| `grout_width` | float | 0.14 | 0.04 to 0.35 | Joint between tesserae as a share of the tessera size. |
| `irregularity` | float | 0.5 | 0 to 1 | Random trimming and tilt of each tessera, as hand-cut pieces have. |
| `outline_rows` | int | 1 | 0 to 3 | Rings of outline colour around each motif. |
| `relief` | float | 0.4 | 0 to 1 | Uneven heights of the tesserae in the bedding mortar. |
| `gloss` | float | 0.2 | 0 to 1 | 0 matte stone tesserae, 1 glossy glass smalti. |
| `colour_variation` | float | 0.5 | 0 to 1 | Spread of tone between tesserae of one colour. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`mosaic_tesserae.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python mosaic_tesserae.py --size 1024 --seed 7 --preset gold_smalti --out textures/mosaic_tesserae
python mosaic_tesserae.py --width 512 --height 256 --set motifs=16 --orm --out maps
```

`--orm` also writes `mosaic_tesserae_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import mosaic_tesserae

maps = mosaic_tesserae.generate(512, 512, seed=3, preset="gold_smalti")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 26.9 s (16 s to compute, 10.9 s to write the PNG files) with a peak of about 561 MB; 256 x 256 takes about 1.66 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/mosaic_tesserae/` of your project (for example `python mosaic_tesserae.py --size 1024 --out path/to/project/baltor/textures/mosaic_tesserae`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.006, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Motifs are discs, so every row is a ring around one disc; figurative designs, borders and andamento along arbitrary curves are out of scope. Tesserae are annular sectors trimmed by random amounts, an approximation of hand-cut squares, and the innermost rings of a motif hold a few wedge-shaped pieces. Gold smalti are drawn as metallic gold faces, not glass over leaf. Occlusion is a blurred-height estimate, not ray traced.
