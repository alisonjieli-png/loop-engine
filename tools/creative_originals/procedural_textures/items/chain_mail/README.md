# Chain mail in the European 4-in-1 weave

Bright steel, blackened matte steel, brass with heavier wire or rusty iron with fine rings. Rings sit on a staggered grid: every row is offset by half a ring, and rows alternate their tilt. Each ring is an annulus with a round wire profile whose height also rises across the ring along its tilt.

Rings are painted with a z-buffer, so in every overlap the higher half wins: each ring passes over two neighbours and under two, the look of interlinked mail. The albedo alpha is 1 on wire and 0 in the gaps. The metal is uniform apart from tarnish (`tarnish`), with darker contact points where rings touch.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `chain_mail_albedo.png` | 4 | sRGB | glTF base colour, values 0.03 to 0.95 |
| `normal` | `chain_mail_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `chain_mail_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `chain_mail_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `chain_mail_height.png` | 1 | linear | white is high |
| `ao` | `chain_mail_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Bright steel mail.
- `blackened`: Blackened steel mail, matte.
- `brass`: Brass mail with heavier wire.
- `rusty`: Rusty iron mail with fine rings.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `rings_across` | int | 8 | 3 to 32 | Rings across the tile in each row. |
| `wire` | float | 0.17 | 0.08 to 0.3 | Wire thickness as a share of the ring spacing. |
| `ring_size` | float | 0.62 | 0.5 to 0.8 | Ring outer radius as a share of the ring spacing. |
| `tilt` | float | 0.5 | 0 to 1 | How steeply rows tilt (stronger interlocking). |
| `tarnish` | float | 0.2 | 0 to 1 | Darkening and dulling of the rings. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`chain_mail.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python chain_mail.py --size 1024 --seed 7 --preset blackened --out textures/chain_mail
python chain_mail.py --width 512 --height 256 --set rings_across=32 --orm --out maps
```

`--orm` also writes `chain_mail_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import chain_mail

maps = chain_mail.generate(512, 512, seed=3, preset="blackened")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17.7 s (8 s to compute, 9.7 s to write the PNG files) with a peak of about 592 MB; 256 x 256 takes about 1.04 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/chain_mail/` of your project (for example `python chain_mail.py --size 1024 --out path/to/project/baltor/textures/chain_mail`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses an alpha scissor at 0.5.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `alphaTest: 0.5`.

## Limits

Rings are flat annuli with a round wire profile, tilted in alternating rows; the over and under is resolved per pixel by height, not by true 3D geometry, so deep overlaps and silhouettes are approximate. The gaps need alpha scissor. Contact shadows are darkened by hand rather than traced. Occlusion is a blurred-height estimate, not ray traced.
