# Human skin pores and micro-relief

Medium-toned and fair facial skin, deep brown facial skin, medium-toned back skin with larger pores, aged fair skin with deep furrows and creases, or freckled skin. Every layer is periodic on the torus, so the detail tiles in both directions over a character's UVs.

`pores`, `pore_size` and `pore_depth` set the pores; `furrows`, `furrow_depth` and `anisotropy` set the polygonal furrow network and how far it stretches along tension lines; `creases` adds the longer wrinkles of aged skin. `redness`, `freckles` and the preset's melanin blotches vary the tone, and `oiliness` lowers the roughness in patches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `skin_pores_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.9 |
| `normal` | `skin_pores_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `skin_pores_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.25 to 0.9 |
| `height` | `skin_pores_height.png` | 1 | linear | white is high |
| `ao` | `skin_pores_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Medium-toned facial skin: fine pores, a light furrow network, some redness.
- `fair`: Fair facial skin with fine pores and soft redness.
- `deep_tone`: Deep brown facial skin with fine pores and a soft sheen.
- `back_medium`: Medium-toned back skin: larger, sparser pores, flatter furrows.
- `aged`: Aged fair skin: deep furrows, creases and blotchy tone.
- `freckled`: Fair freckled skin with light redness.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pores` | int | 64 | 16 to 160 | Pore grid cells across the tile (pore spacing). |
| `pore_size` | float | 0.3 | 0.1 to 0.6 | Pore radius as a share of the pore spacing. |
| `pore_depth` | float | 0.5 | 0 to 1 | How deep the pores are. |
| `furrows` | int | 22 | 6 to 60 | Cells of the furrow network across the tile. |
| `furrow_depth` | float | 0.4 | 0 to 1 | Depth of the fine furrow network. |
| `anisotropy` | float | 0.4 | 0 to 1 | How much the furrow cells stretch across the tile (tension lines). |
| `creases` | float | 0 | 0 to 1 | Longer wrinkles of aged skin. |
| `redness` | float | 0.3 | 0 to 1 | Blotchy redness from blood near the surface. |
| `freckles` | float | 0 | 0 to 1 | Density of freckles. |
| `oiliness` | float | 0.4 | 0 to 1 | Patches of lower roughness, as oily skin shows. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`skin_pores.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python skin_pores.py --size 1024 --seed 7 --preset fair --out textures/skin_pores
python skin_pores.py --width 512 --height 256 --set pores=160 --orm --out maps
```

`--orm` also writes `skin_pores_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import skin_pores

maps = skin_pores.generate(512, 512, seed=3, preset="fair")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 35.9 s (21.3 s to compute, 14.5 s to write the PNG files) with a peak of about 855 MB; 256 x 256 takes about 2.18 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/skin_pores/` of your project (for example `python skin_pores.py --size 1024 --out path/to/project/baltor/textures/skin_pores`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.8) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

For a character, blend the normal map over the character's own normal map (for example with a detail-normal blend) and use the albedo at low opacity as a tint, so the face or body keeps its own colour layout.

## Limits

This is tiling micro-detail, not a full skin material: there is no subsurface scattering, no colour map of a face or body, and no layout by region (nose, forehead, cheek). Pores sit on a jittered grid, furrows are borders of warped anisotropic cells and creases are ridged noise, all stylized approximations of real dermal structure. Skin tones are artistic presets, not measured; use the albedo as a tint or overlay over a character's own colour. Relief is small, so the normal map carries most of the effect. Occlusion is a blurred-height estimate.
