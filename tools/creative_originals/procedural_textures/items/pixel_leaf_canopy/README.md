# Pixel-art tree canopy of shaded leaf clumps

A summer broadleaf canopy with apples, an autumn mix of orange, red and yellow clumps, pink cherry blossom or a dark conifer canopy, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Round clumps sit on Poisson-disc points of the torus, closer together than their size so they overlap, and are painted from the top of the tile to the bottom so lower clumps cover higher ones.

Inside a clump the offset from its centre along a light from the top left picks one of four tones, the rim facing away from the light is outlined in the darkest tone, and the outline is scalloped by a sine of the angle. Hashed two-pixel leaves (or periodic needle strokes when `needles` is 1) break the tone bands, the deep gap colour shows where no clump reaches, and `fruit` adds fruit or blossoms.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_leaf_canopy_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_leaf_canopy_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_leaf_canopy_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `pixel_leaf_canopy_height.png` | 1 | linear | white is high |
| `ao` | `pixel_leaf_canopy_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Summer broadleaf canopy with a few red apples.
- `autumn`: Autumn canopy mixing orange, red and yellow clumps.
- `cherry_blossom`: Pink blossom canopy with white petals.
- `pine`: Dark blue-green conifer canopy of needle strokes.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `clump_radius` | float | 4.5 | 2.5 to 7 | Radius of a leaf clump in art pixels. |
| `coverage` | float | 0.9 | 0.3 to 1 | Share of the clump positions that hold a clump; lower values open more gaps. |
| `leaf_texture` | float | 0.5 | 0 to 1 | How strongly single leaves break up the tone bands. |
| `needles` | int | 0 | 0 to 1 | 1 draws short needle strokes instead of round leaves (conifers). |
| `fruit` | float | 0.1 | 0 to 1 | Density of fruit or blossoms on the clumps. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_leaf_canopy.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_leaf_canopy.py --size 1024 --seed 7 --preset autumn --out textures/pixel_leaf_canopy
python pixel_leaf_canopy.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_leaf_canopy_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_leaf_canopy

maps = pixel_leaf_canopy.generate(512, 512, seed=3, preset="autumn")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 7.4 s (0.7 s to compute, 6.7 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.6 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_leaf_canopy/` of your project (for example `python pixel_leaf_canopy.py --size 1024 --out path/to/project/baltor/textures/pixel_leaf_canopy`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

Stylized pixel art with the light from the top left baked into the clump shading; clumps are scalloped discs with a dome height, not individual modelled leaves or branches. Clumps are painted from the top of the tile to the bottom, which suits a canopy seen from the front or slightly above. Fruit and blossoms are tiny fixed sprites. The normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
