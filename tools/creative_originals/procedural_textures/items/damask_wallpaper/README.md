# Damask wallpaper with a grown symmetric ornament

Ivory satin damask tone on tone, a metallic gold motif printed on matte burgundy, raised black velvet flock on a silver ground, or a flat teal print on cream. The ornament is grown from the seed on the right half of a cell and mirrored: a central stem with a bud and a body, a palmette fan of petals at the top, pairs of scrolls that leave the stem and curl ever tighter into spirals, leaves along the scrolls and berries at their tips.

Every cell of a half-drop lattice receives the ornament, with a small rosette in the gaps between neighbours. As in woven damask, the motif can share the ground's colour and differ only in weave direction: fine stripes run one way in the motif and across it in the ground, which shows as satin sheen in the roughness and colour. Relief raises the motif for embossed paper or flock, and the gold preset makes it metallic.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `damask_wallpaper_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.95 |
| `normal` | `damask_wallpaper_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `damask_wallpaper_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `metallic` | `damask_wallpaper_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `damask_wallpaper_height.png` | 1 | linear | white is high |
| `ao` | `damask_wallpaper_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Ivory satin damask: tone on tone, the motif shining against a matte ground.
- `burgundy_gold`: Metallic gold motif printed on matte deep burgundy.
- `flocked_velvet`: Raised black velvet flock on a silver sheen ground.
- `teal_print`: Flat teal print on cream paper, smaller motifs, no weave.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `column_pairs` | int | 1 | 1 to 4 | Pairs of motif columns across the tile (the half-drop repeats every two columns). |
| `scrolls` | int | 3 | 1 to 4 | Pairs of scrolls leaving the stem. |
| `petals` | int | 7 | 3 to 11 | Petals in the palmette fan at the top of the motif. |
| `leafiness` | float | 0.7 | 0 to 1 | Leaves set along the scrolls. |
| `stroke` | float | 1 | 0.5 to 2 | Width of the stems and scrolls. |
| `relief` | float | 0.3 | 0 to 1 | Embossed or flocked height of the motif. |
| `weave` | float | 0.7 | 0 to 1 | Strength of the crossed weave stripes that set satin motif against matte ground. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`damask_wallpaper.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python damask_wallpaper.py --size 1024 --seed 7 --preset burgundy_gold --out textures/damask_wallpaper
python damask_wallpaper.py --width 512 --height 256 --set column_pairs=4 --orm --out maps
```

`--orm` also writes `damask_wallpaper_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import damask_wallpaper

maps = damask_wallpaper.generate(512, 512, seed=3, preset="burgundy_gold")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 23.6 s (7.7 s to compute, 15.8 s to write the PNG files) with a peak of about 614 MB; 256 x 256 takes about 1.42 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/damask_wallpaper/` of your project (for example `python damask_wallpaper.py --size 1024 --out path/to/project/baltor/textures/damask_wallpaper`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.003, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The ornament is assembled from capsules and ellipses by a seeded grammar, so it is a simplified damask-like motif without the outlines, hatching and interlaced detail of a designed damask. The satin effect is approximated by crossed sine stripes in colour and roughness, not by an anisotropic weave model, and the stripes alias below about three pixels per stripe. Flock and emboss are height from a blurred mask. Occlusion is a blurred-height estimate.
