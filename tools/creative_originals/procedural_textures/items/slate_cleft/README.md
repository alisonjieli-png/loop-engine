# Riven slate

Blue-grey, green, heather, rusty or honed black slate. Slate splits along its cleavage into thin sheets, so a riven face is a set of nearly flat terraces with short steps between them. A warped fractal is quantized into `terraces` levels, and the step edges are smoothed over `step_softness`.

Each terrace takes its own tone, the step faces darken and their lips catch a little light, fine streaks add the riving texture, and `iron_spots` leaves rusty halos from weathered pyrite.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `slate_cleft_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.7 |
| `normal` | `slate_cleft_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `slate_cleft_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.25 to 1 |
| `height` | `slate_cleft_height.png` | 1 | linear | white is high |
| `ao` | `slate_cleft_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Blue-grey riven slate with a few rust spots.
- `green`: Grey-green slate with broad, soft terraces.
- `heather`: Purple-grey slate with crisp steps.
- `rusty_multicolour`: Grey slate stained with heavy rust and ochre.
- `black_honed`: Fine black slate, honed nearly flat.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `terraces` | int | 7 | 2 to 20 | Cleavage levels over the height range. |
| `terrace_scale` | int | 3 | 1 to 10 | Noise cells across the tile for the terrace outlines (higher gives smaller terraces). |
| `step_softness` | float | 0.15 | 0.02 to 0.5 | Share of each level spent on the step edge (low values give crisp steps). |
| `riving` | float | 0.5 | 0 to 1 | Depth of the fine streaks along the cleavage. |
| `iron_spots` | float | 0.15 | 0 to 1 | Rusty spots from weathered pyrite. |
| `tone_variation` | float | 0.5 | 0 to 1 | Tone change between terraces. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`slate_cleft.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python slate_cleft.py --size 1024 --seed 7 --preset green --out textures/slate_cleft
python slate_cleft.py --width 512 --height 256 --set terraces=20 --orm --out maps
```

`--orm` also writes `slate_cleft_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import slate_cleft

maps = slate_cleft.generate(512, 512, seed=3, preset="green")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 21 s (11.9 s to compute, 9 s to write the PNG files) with a peak of about 687 MB; 256 x 256 takes about 1.19 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/slate_cleft/` of your project (for example `python slate_cleft.py --size 1024 --out path/to/project/baltor/textures/slate_cleft`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

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

Terraces are a quantized noise field, an approximation of cleavage; real slate also shows cleavage steps along straight lines, which this does not force. Iron spots are round stamps. Occlusion is a blurred-height estimate.
