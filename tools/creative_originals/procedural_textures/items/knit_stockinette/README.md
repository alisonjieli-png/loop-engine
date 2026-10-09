# Knitted fabric in five stitch patterns

Cream jumper knit, chunky red stockinette, navy k2p2 rib, heather garter, Fair Isle colourwork or moss green seed stitch. The tile holds whole numbers of stitch columns and rows, rounded so rib, stripes and motifs repeat, so the fabric tiles in both directions.

A knit stitch is drawn as a V of two slanted yarn legs whose upper ends dip behind the stitch above; a purl stitch is a horizontal wave of yarn, arching over the loop head and dipping at the sinker loop. `pattern` decides per stitch which one shows, and rib and garter sink their purl or knit stitches between the raised ones. Twisted plies cut diagonal grooves across the legs, `fuzz` adds a soft halo and heather flecks, and `irregularity` gives each stitch its own offset, size and tone. `colourwork` adds contrast stripes or a stranded motif.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `knit_stockinette_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `knit_stockinette_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `knit_stockinette_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.55 to 1 |
| `height` | `knit_stockinette_height.png` | 1 | linear | white is high |
| `ao` | `knit_stockinette_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Cream wool in stockinette, a fine jumper knit.
- `chunky_red`: Thick red yarn in stockinette with strongly twisted plies.
- `navy_rib`: Navy k2p2 ribbing as on cuffs and hems, the purl columns sunk between the knit.
- `heather_garter`: Grey heather yarn in garter stitch: ridges of purl bumps.
- `fair_isle`: Stranded colourwork: a navy motif on cream stockinette.
- `moss_seed`: Moss green seed stitch with a pebbly surface and contrast stripes.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 4 | 0 stockinette (all knit), 1 reverse stockinette (all purl), 2 garter (knit and purl rows alternate), 3 k2p2 rib (two knit columns, two purl columns), 4 seed stitch (knit and purl alternate in both directions). |
| `stitches` | int | 16 | 4 to 48 | Stitch columns across the tile width; rounded up to a multiple of 4 for rib and of 8 for a motif. |
| `row_ratio` | float | 1.4 | 1 to 1.8 | Rows per stitch width (the gauge); the row count is rounded to keep the pattern repeating. |
| `yarn_width` | float | 1 | 0.7 to 1.25 | Yarn thickness relative to the stitch: low values open gaps between the legs. |
| `twist` | float | 0.5 | 0 to 1 | Depth of the diagonal grooves between twisted plies. |
| `plies` | float | 3.5 | 1.5 to 6 | Ply twists along one stitch leg. |
| `fuzz` | float | 0.4 | 0 to 1 | Fibre halo: fine noise in height and colour, and rougher yarn. |
| `irregularity` | float | 0.4 | 0 to 1 | Hand-knit unevenness: per-stitch offset, size and tone. |
| `colourwork` | int | 0 | 0 to 2 | 0 one colour, 1 contrast stripes two rows in six, 2 a stranded two-colour motif repeating every eight stitches and rows. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`knit_stockinette.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python knit_stockinette.py --size 1024 --seed 7 --preset chunky_red --out textures/knit_stockinette
python knit_stockinette.py --width 512 --height 256 --set pattern=4 --orm --out maps
```

`--orm` also writes `knit_stockinette_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import knit_stockinette

maps = knit_stockinette.generate(512, 512, seed=3, preset="chunky_red")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 19 s (9.9 s to compute, 9.1 s to write the PNG files) with a peak of about 518 MB; 256 x 256 takes about 1 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/knit_stockinette/` of your project (for example `python knit_stockinette.py --size 1024 --out path/to/project/baltor/textures/knit_stockinette`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.008, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Stitches are stylized yarn domes on a regular grid: knit legs are superellipses and a purl stitch is a cosine-shaped yarn path, not a simulated loop structure. Cables, increases, decreases and lace holes are out of scope, and the stranded motif is a symmetric 8 x 8 chart chosen by the seed. The fabric is flat, with no drape or stretch. Ply grooves fade out where they would be finer than a few pixels. Occlusion is a blurred-height estimate, not ray traced. Colours are artistic, not measured yarn.
