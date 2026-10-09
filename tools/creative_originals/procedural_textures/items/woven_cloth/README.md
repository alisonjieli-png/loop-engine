# Woven cloth from a weave draft

Linen, denim, wool twill, satin, burlap, basket weave or herringbone. The tile holds a whole number of warp threads (running down the image) and weft threads (running across). A draft, a small binary matrix repeated over the threads, says at each crossing whether the warp or the weft lies on top; thread counts are rounded up to a multiple of the draft so the weave repeats.

The visible thread has a round cross-section and dips only where it passes under the next crossing, so twill and satin floats stay raised. Twist striations, fuzz, slubs and per-thread colour come from noise and hashes of the thread index; narrow threads open gaps that show the dark backing.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `woven_cloth_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `woven_cloth_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `woven_cloth_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.25 to 1 |
| `height` | `woven_cloth_height.png` | 1 | linear | white is high |
| `ao` | `woven_cloth_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Natural linen in plain weave with slubs.
- `denim`: Indigo warp and white weft in 3/1 twill.
- `wool_twill`: Charcoal and grey wool in 2/2 twill with soft fuzz.
- `satin`: Burgundy 4/1 satin with long glossy floats.
- `burlap`: Coarse open jute in plain weave with gaps and hairy fibres.
- `basket`: Off-white cotton in 2/2 basket weave.
- `herringbone`: Brown and cream wool herringbone twill.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `weave` | int | 0 | 0 to 5 | Draft: 0 plain, 1 2/2 twill, 2 3/1 twill, 3 4/1 satin, 4 2/2 basket, 5 herringbone twill. |
| `threads` | int | 24 | 4 to 96 | Warp and weft threads across the tile (rounded up to a multiple of the draft size). |
| `thread_width` | float | 0.88 | 0.5 to 1 | Thread width as a share of the thread spacing; lower values open gaps between threads. |
| `twist` | float | 0.5 | 0 to 1 | Depth of the diagonal twist striations along each thread. |
| `fuzz` | float | 0.4 | 0 to 1 | Loose fibre noise on the thread surface. |
| `slubs` | float | 0.3 | 0 to 1 | Irregular thick and thin stretches and colour changes along the threads. |
| `sheen` | float | 0 | 0 to 1 | Lowers roughness on long floats, as in satin. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`woven_cloth.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python woven_cloth.py --size 1024 --seed 7 --preset denim --out textures/woven_cloth
python woven_cloth.py --width 512 --height 256 --set weave=5 --orm --out maps
```

`--orm` also writes `woven_cloth_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import woven_cloth

maps = woven_cloth.generate(512, 512, seed=3, preset="denim")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 23.9 s (10.7 s to compute, 13.1 s to write the PNG files) with a peak of about 599 MB; 256 x 256 takes about 1.33 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/woven_cloth/` of your project (for example `python woven_cloth.py --size 1024 --out path/to/project/baltor/textures/woven_cloth`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Threads are idealized round strands on a regular grid with no fabric drape, stretch or pile. Thread counts are rounded up to a multiple of the draft size. Sheen is approximated by lower roughness on floats; anisotropic highlights need an engine-side fabric shader. Occlusion is a blurred-height estimate.
