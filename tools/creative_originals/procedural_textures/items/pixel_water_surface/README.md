# Pixel-art water surface with wave glyphs and caustics

Open sea, clear lagoon shallows, a still swamp or rough rapids, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Three depth shades come from periodic noise with an ordered Bayer dither on their borders.

Waves are the classic glyph of pixel-art water: a short light dash over two darker end pixels, placed by Poisson-disc sampling on the torus so they spread evenly without a visible grid. Sparkles are single bright pixels or small crosses. `caustics` draws the one-pixel border lines of a Voronoi diagram masked by noise, and `foam` adds clusters with dithered edges. Roughness stays low on open water and rises on foam.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_water_surface_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_water_surface_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_water_surface_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 0.95 |
| `height` | `pixel_water_surface_height.png` | 1 | linear | white is high |
| `ao` | `pixel_water_surface_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Open sea blue with white wave glyphs and sparkles.
- `shallow_lagoon`: Clear turquoise shallows with a caustic light network.
- `swamp`: Still murky green water with a few ripples and scum.
- `rapids`: Rough grey-blue river water with long waves and foam.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `waves` | float | 0.6 | 0 to 1 | Share of the evenly spread wave positions that get a wave glyph. |
| `wave_length` | int | 3 | 2 to 6 | Length of the light dash of a wave glyph in art pixels. |
| `sparkles` | float | 0.3 | 0 to 1 | Density of bright sparkles. |
| `caustics` | float | 0 | 0 to 1 | Coverage of the caustic light network of shallow water. |
| `foam` | float | 0 | 0 to 1 | Coverage of foam clusters. |
| `depth_patches` | float | 0.6 | 0 to 1 | Contrast of the deep and shallow patches. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_water_surface.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_water_surface.py --size 1024 --seed 7 --preset shallow_lagoon --out textures/pixel_water_surface
python pixel_water_surface.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_water_surface_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_water_surface

maps = pixel_water_surface.generate(512, 512, seed=3, preset="shallow_lagoon")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 7.9 s (0.9 s to compute, 7 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.6 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_water_surface/` of your project (for example `python pixel_water_surface.py --size 1024 --out path/to/project/baltor/textures/pixel_water_surface`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

A still frame of stylized pixel art, not a wave simulation, and it does not animate; for motion, scroll the tile or swap seeds. The light from the top left is baked into the wave glyph colours. Caustics are a Voronoi line pattern, not traced light. Roughness and height are values per drawn class, and the normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
