# Carbon fibre weave and forged carbon

Black 2x2 twill under gloss, plain weave with wide tows, marbled forged carbon, a yellow aramid and carbon hybrid, and matte dry twill. Woven styles lay tows, flat bundles of fibres, on a grid; a draft decides which tow is on top at each crossing. A tow carries fine fibre lines along its own direction, a rounded cross-section and darker ends where it dives under.

Tows running across the tile reflect differently from tows running down it (`sheen`), the anisotropic shimmer that makes a carbon weave visible. Forged carbon is chopped fibre pressed flat: Voronoi patches, each with its own fibre direction, measured from the patch nucleus on the torus so patches crossing the tile edge stay continuous. Carbon is not metallic, so the item writes no metallic map.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `carbon_fibre_albedo.png` | 3 | sRGB | glTF base colour, values 0.01 to 0.8 |
| `normal` | `carbon_fibre_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `carbon_fibre_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 0.8 |
| `height` | `carbon_fibre_height.png` | 1 | linear | white is high |
| `ao` | `carbon_fibre_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Black 2x2 twill carbon under gloss clear coat.
- `plain_weave`: Plain-weave carbon with wide tows.
- `forged`: Forged carbon with marbled chopped-fibre patches.
- `kevlar_hybrid`: Yellow aramid and black carbon tows in twill.
- `matte_dry`: Uncoated dry twill with a matte finish.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `style` | int | 0 | 0 to 2 | Construction: 0 2x2 twill, 1 plain weave, 2 forged (chopped fibre). |
| `tows_across` | int | 16 | 4 to 64 | Tows across the tile (rounded up to a multiple of the weave repeat); forged patches scale with it. |
| `sheen` | float | 0.6 | 0 to 1 | Brightness difference between tow directions. |
| `clear_coat` | float | 0.85 | 0 to 1 | Gloss of the clear coat (0 dry matte weave, 1 deep gloss). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`carbon_fibre.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python carbon_fibre.py --size 1024 --seed 7 --preset plain_weave --out textures/carbon_fibre
python carbon_fibre.py --width 512 --height 256 --set style=2 --orm --out maps
```

`--orm` also writes `carbon_fibre_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import carbon_fibre

maps = carbon_fibre.generate(512, 512, seed=3, preset="plain_weave")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 11.2 s (5.2 s to compute, 6 s to write the PNG files) with a peak of about 469 MB; 256 x 256 takes about 0.73 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/carbon_fibre/` of your project (for example `python carbon_fibre.py --size 1024 --out path/to/project/baltor/textures/carbon_fibre`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.8) and the height map through a Displacement node (scale 0.001, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The sheen of each tow direction is baked into albedo and roughness; real weave shifts with the view and light angle, which needs an anisotropic shader. Forged carbon patches are Voronoi cells, a simplification of pressed chopped fibre. A clear coat is approximated by low roughness; add a clear coat layer in your engine for its second reflection. Occlusion is a blurred-height estimate, not ray traced.
