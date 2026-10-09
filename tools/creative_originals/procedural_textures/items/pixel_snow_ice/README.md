# Pixel-art snow drifts and glossy ice patches

Fresh snow, a frozen pond, grey trodden snow or blue glacier ice, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Snow is a field of rounded drift mounds: every cell of a Voronoi diagram is a mound, and the offset of a pixel from its seed along a light from the top left sets one of three snow shades with a Bayer dither between them, so each mound has a bright cap and a cold shadowed foot.

Ice patches cover about `ice` of the tile where a periodic noise crosses a threshold: flat glossy ice with broken diagonal highlight streaks every `streak_spacing` pixels, a darker rim where the ice meets the snow below and to the right, and random-walk cracks. Sparkles are single bright pixels or four-point stars, and `dirt` scatters brown specks over trodden snow.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_snow_ice_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_snow_ice_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_snow_ice_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `height` | `pixel_snow_ice_height.png` | 1 | linear | white is high |
| `ao` | `pixel_snow_ice_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Fresh lumpy snow with sparkles and a few ice patches.
- `frozen_pond`: Mostly glossy pond ice with cracks and small snow drifts.
- `packed_snow`: Grey trodden snow with dirt specks, few sparkles and no ice.
- `glacier`: Deep blue glacier ice crossed by cracks, with white snow patches.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `mounds` | int | 5 | 2 to 8 | Snow drift mounds across the tile. |
| `ice` | float | 0.3 | 0 to 1 | Share of the tile covered by ice patches. |
| `streak_spacing` | int | 5 | 3 to 9 | Distance between the diagonal highlight streaks on ice, in art pixels. |
| `cracks` | float | 0.3 | 0 to 1 | Number of cracks in the ice. |
| `sparkles` | float | 0.4 | 0 to 1 | Density of sparkles on the snow. |
| `dirt` | float | 0 | 0 to 1 | Density of dirt specks on trodden snow. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_snow_ice.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_snow_ice.py --size 1024 --seed 7 --preset frozen_pond --out textures/pixel_snow_ice
python pixel_snow_ice.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_snow_ice_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_snow_ice

maps = pixel_snow_ice.generate(512, 512, seed=3, preset="frozen_pond")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 9 s (0.9 s to compute, 8 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.65 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_snow_ice/` of your project (for example `python pixel_snow_ice.py --size 1024 --out path/to/project/baltor/textures/pixel_snow_ice`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

Stylized pixel art with the light from the top left baked into the mound shading and the ice rims; drifts are Voronoi mounds and ice patches thresholded noise, not a snow or freezing model. Streaks are fixed diagonal highlights, not reflections of the scene. Roughness and height are values per drawn class, and the normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
