# Versailles pattern stone pavers

Tumbled ivory travertine, banded walnut travertine, honed limestone or multicolour slate in the four-size Versailles pattern. One piece of each size (2 x 3, 2 x 2, 1 x 2 and 1 x 1 units) forms a cluster that the lattice of points (t, 4t mod 13) repeats, so 13 clusters fill a 13 x 13 unit tile exactly; `repeats` puts more copies on one tile.

The module was found by an exhaustive search for clusters that tile by such a lattice with no point where four pieces meet and no straight joint longer than four units, and `generate()` re-measures both properties before it draws. Each piece is tumbled stone: `tumbling` rounds and chips the edges, `pits` opens travertine holes and `veining` draws bands along the piece's bedding, which turns with the piece. Joints are filled with sand or grout to `joint_fill`.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `versailles_pavers_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.9 |
| `normal` | `versailles_pavers_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `versailles_pavers_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `versailles_pavers_height.png` | 1 | linear | white is high |
| `ao` | `versailles_pavers_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Tumbled ivory travertine in the Versailles pattern with sand joints.
- `walnut_travertine`: Darker walnut and noce travertine, strongly banded and pitted.
- `honed_limestone`: Honed limestone with crisp sawn edges, few pits and thin grout joints.
- `multicolour_slate`: Gauged slate in grey, rust and green, two pattern repeats per tile.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `repeats` | int | 1 | 1 to 3 | Copies of the 13 x 13 unit pattern across the tile. |
| `joint_width` | float | 0.05 | 0.01 to 0.15 | Joint width in units (the side of the smallest square). |
| `joint_fill` | float | 0.55 | 0 to 0.95 | Height of the jointing sand or grout relative to the stone faces. |
| `tumbling` | float | 0.6 | 0 to 1 | Rounded, chipped and worn edges from tumbling: 0 crisp sawn edges. |
| `pits` | float | 0.5 | 0 to 1 | Travertine holes elongated along each piece's bedding. |
| `veining` | float | 0.4 | 0 to 1 | Banded colour along the bedding of each piece. |
| `colour_variation` | float | 0.6 | 0 to 1 | Spread of colour between pieces. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`versailles_pavers.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python versailles_pavers.py --size 1024 --seed 7 --preset walnut_travertine --out textures/versailles_pavers
python versailles_pavers.py --width 512 --height 256 --set repeats=3 --orm --out maps
```

`--orm` also writes `versailles_pavers_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import versailles_pavers

maps = versailles_pavers.generate(512, 512, seed=3, preset="walnut_travertine")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 35.4 s (24.7 s to compute, 10.7 s to write the PNG files) with a peak of about 720 MB; 256 x 256 takes about 2.65 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/versailles_pavers/` of your project (for example `python versailles_pavers.py --size 1024 --out path/to/project/baltor/textures/versailles_pavers`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.2). Change `uv1_scale` to repeat the tile.

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

One fixed module: one piece each of 2 x 3, 2 x 2, 1 x 2 and 1 x 1 units repeated by a lattice of index 13, so the tile is 13 units square (or a multiple); other Versailles layouts and borders are out of scope. Travertine pits, bands, chips and slate colours are noise approximations, not measured stone. At small output sizes joints are thinner than a pixel. Occlusion is a blurred-height estimate, not ray traced.
