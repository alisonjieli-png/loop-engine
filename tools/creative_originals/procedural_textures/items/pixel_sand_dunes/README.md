# Pixel-art sand with dithered dunes and ripples

Warm beach sand, orange desert dunes, white coral sand or black volcanic sand, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Broad dunes are a periodic wave whose phase is bent by noise; its slope becomes three sand shades, and an ordered 4 x 4 Bayer dither turns the smooth slope into the stepped checker gradients of hand-made pixel art.

Wind ripples are lines of a wave with whole-number frequencies across and down the tile, bent by a sine and by noise: the crest pixel takes the light colour and the pixel below it the shadow colour, and a noise mask keeps ripples to patches covering about `ripples` of the sand. Shells and pebbles are small sprites scattered with wrap-around.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_sand_dunes_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.98 |
| `normal` | `pixel_sand_dunes_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_sand_dunes_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `pixel_sand_dunes_height.png` | 1 | linear | white is high |
| `ao` | `pixel_sand_dunes_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Warm beach sand with ripples, shells and a few pebbles.
- `desert_dunes`: Orange desert dunes with strong shading and long ripples, no shells.
- `white_coral`: Bright white coral sand scattered with shells and coral bits.
- `black_sand`: Black volcanic sand with grey pebbles and pale glints.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `dunes` | int | 1 | 1 to 3 | Dune waves down the tile. |
| `dune_shading` | float | 0.45 | 0 to 1 | Contrast of the dithered dune shading. |
| `ripple_spacing` | int | 5 | 3 to 8 | Distance between wind ripple lines in art pixels. |
| `ripple_slant` | int | 1 | -2 to 2 | Slant of the ripple lines: whole steps of rise across the tile. |
| `ripples` | float | 0.6 | 0 to 1 | Share of the sand covered by ripple patches. |
| `shells` | float | 0.3 | 0 to 1 | Density of shells. |
| `pebbles` | float | 0.2 | 0 to 1 | Density of pebbles. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_sand_dunes.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_sand_dunes.py --size 1024 --seed 7 --preset desert_dunes --out textures/pixel_sand_dunes
python pixel_sand_dunes.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_sand_dunes_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_sand_dunes

maps = pixel_sand_dunes.generate(512, 512, seed=3, preset="desert_dunes")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 8.9 s (1 s to compute, 7.8 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.56 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_sand_dunes/` of your project (for example `python pixel_sand_dunes.py --size 1024 --out path/to/project/baltor/textures/pixel_sand_dunes`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

Stylized pixel art with the light from the top left baked into the shading; dunes and ripples are periodic waves bent by noise, not a wind or sediment model. Ripple frequencies are whole numbers across and down the tile so the pattern repeats exactly, which limits slants to whole steps. Shells and pebbles are tiny fixed sprites. The normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
