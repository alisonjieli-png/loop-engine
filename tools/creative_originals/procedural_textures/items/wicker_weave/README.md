# Open wicker weave of reeds over stakes

Honey rattan in plain randing, worn white-painted wicker, espresso double randing or grey-brown willow woven over two and under two. Stakes run down the tile and weavers across it, with counts rounded so the weave pattern repeats and the tile wraps in both directions.

Each weaver has a depth at every stake, over or under according to `pattern`, and bends between them; at each pixel the higher rod is visible, and where no rod covers the pixel the alpha is zero. `stake_width` and `weaver_width` open or close the gaps, `bulge` sets how far the weavers bend, `fibres` adds streaks, tone and nodes, and `paint_wear` lets painted wicker wear through to the reed on its high points.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `wicker_weave_albedo.png` | 4 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `wicker_weave_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `wicker_weave_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `wicker_weave_height.png` | 1 | linear | white is high |
| `ao` | `wicker_weave_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Natural honey rattan in plain randing.
- `white_painted`: White-painted wicker with the paint worn through on the high points.
- `dark_stained`: Espresso-stained wicker in double randing.
- `willow_twill`: Grey-brown willow, over two and under two, with wide gaps.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 2 | 0 randing (over one stake, under one), 1 double randing (weavers in pairs), 2 over two and under two, stepping one stake per row. |
| `stakes` | int | 10 | 4 to 32 | Upright stakes across the tile; rounded up to keep the pattern repeating. |
| `weavers` | int | 22 | 6 to 64 | Weavers down the tile; rounded up to keep the pattern repeating. |
| `stake_width` | float | 0.5 | 0.25 to 0.9 | Stake diameter as a share of the stake spacing. |
| `weaver_width` | float | 0.88 | 0.5 to 1 | Weaver diameter as a share of the weaver spacing; below 1 light shows between weavers. |
| `bulge` | float | 0.8 | 0.2 to 1 | How far the weavers bend over and under the stakes. |
| `fibres` | float | 0.5 | 0 to 1 | Fibre streaks, tone differences and nodes along the reeds. |
| `paint_wear` | float | 0 | 0 to 1 | On painted presets, how much of the paint has worn through to the reed on high points. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`wicker_weave.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python wicker_weave.py --size 1024 --seed 7 --preset white_painted --out textures/wicker_weave
python wicker_weave.py --width 512 --height 256 --set pattern=2 --orm --out maps
```

`--orm` also writes `wicker_weave_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import wicker_weave

maps = wicker_weave.generate(512, 512, seed=3, preset="white_painted")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 21.2 s (9.5 s to compute, 11.7 s to write the PNG files) with a peak of about 594 MB; 256 x 256 takes about 1.31 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/wicker_weave/` of your project (for example `python wicker_weave.py --size 1024 --out path/to/project/baltor/textures/wicker_weave`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses an alpha scissor at 0.5.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.01, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `alphaTest: 0.5`.

## Limits

Reeds are ideal round rods with a cosine bend around the stakes; they do not flatten where they cross, and stakes stay straight. Borders, rims, chair-caning hexagons and twined (pairing) weaves are out of scope. The gaps are an alpha cut-out at 0.5, so the material needs alpha scissor (set in the Godot template and the Blender builder); behind the gaps the albedo is a dark reed colour. Occlusion is a blurred-height estimate that ignores the open gaps. Colours are artistic.
