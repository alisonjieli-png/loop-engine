# Pixel-art sky with puffy outlined clouds

A blue day sky with white outlined cumulus, an orange sunset with violet clouds lit gold, a night sky with stars or a heavy storm, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. The sky is one flat colour broken into faint patches by an ordered dither of low-frequency noise, so the tile repeats vertically as well as horizontally.

Clouds sit at Poisson-disc points and are painted from the top of the tile down, so lower clouds pass in front. Each is a union of round puffs: small puffs along a flat base and larger ones heaped above by `puffiness`. The puff a pixel lies in sets its tone along a light from the top left, the two rows above the base stay in shade, `outline` rings each cloud with a one-pixel line and `stars` scatters stars in the open sky.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_cloud_sky_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_cloud_sky_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_cloud_sky_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `pixel_cloud_sky_height.png` | 1 | linear | white is high |
| `ao` | `pixel_cloud_sky_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Blue day sky with white outlined cumulus clouds.
- `sunset`: Orange and pink evening sky with violet clouds lit gold from above.
- `night`: Dark navy night sky with grey-blue clouds and stars.
- `storm`: Heavy grey storm clouds filling a dark grey sky.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `clouds` | float | 0.7 | 0 to 1 | Share of the evenly spread cloud positions that hold a cloud. |
| `cloud_width` | float | 12 | 6 to 24 | Typical cloud width in art pixels. |
| `puffiness` | float | 0.6 | 0 to 1 | Height of the puffs heaped above the cloud base. |
| `outline` | int | 1 | 0 to 1 | 1 rings each cloud with a one-pixel outline. |
| `stars` | float | 0 | 0 to 1 | Density of stars in the open sky. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_cloud_sky.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_cloud_sky.py --size 1024 --seed 7 --preset sunset --out textures/pixel_cloud_sky
python pixel_cloud_sky.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_cloud_sky_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_cloud_sky

maps = pixel_cloud_sky.generate(512, 512, seed=3, preset="sunset")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 6 s (0.7 s to compute, 5.3 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.35 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_cloud_sky/` of your project (for example `python pixel_cloud_sky.py --size 1024 --out path/to/project/baltor/textures/pixel_cloud_sky`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.6) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

For Godot 2D, use the albedo PNG as a repeating background (a TextureRect or ParallaxBackground with texture filter nearest); the normal PNG suits a CanvasTexture when the sky should react to 2D lights. `material.tres` is a StandardMaterial3D for 3D use. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

A still frame of stylized pixel art, not a cloud simulation; for parallax motion, scroll the tile. The sky has no vertical gradient, because a gradient would not repeat vertically. Clouds are unions of circles with a flat base, painted from the top of the tile down, and the light from the top left is baked into their tones. Height and roughness only matter for lit 2D or 3D use. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
