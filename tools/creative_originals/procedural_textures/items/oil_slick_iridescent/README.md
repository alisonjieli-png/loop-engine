# Iridescent oil slick from thin-film interference

Oil floating on puddles in dark asphalt, a spill spread across harbour water, a soap film in air that turns black where it is thinnest, or heat tint on steel in straw, bronze, purple and blue bands beside weld lines. A film thickness field, domain-warped fractal noise in swirls or bands that thin away from weld lines, is turned into colour by two-beam interference: the reflectance at each wavelength is r1^2 + r2^2 + 2 r1 r2 cos(4 pi n d / lambda), with Fresnel amplitudes from the preset's refractive indices.

That spectrum is weighted by a 6500 K illuminant, integrated against a multi-lobe Gaussian fit of the CIE 1931 colour-matching functions and converted to linear sRGB; a table over thickness makes it one lookup per pixel. On asphalt the liquid fills the hollows of the stone height field up to the level set by `coverage`, so puddles are flat and glossy while the dry stone stays rough. Heat-tinted steel is a metal: the metallic map is 1 and its film colour is the metallic base colour.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `oil_slick_iridescent_albedo.png` | 3 | sRGB | glTF base colour, values 0.01 to 0.95 |
| `normal` | `oil_slick_iridescent_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `oil_slick_iridescent_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.03 to 0.95 |
| `metallic` | `oil_slick_iridescent_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `oil_slick_iridescent_height.png` | 1 | linear | white is high |
| `ao` | `oil_slick_iridescent_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Oil on puddles in dark asphalt: rainbow swirls on flat water, dry rough stone around.
- `harbour_water`: A spill on dark harbour water covering the whole surface in broad swirls.
- `soap_film`: Soap film in air: vivid swirling bands that go black where the film is thinnest.
- `tempered_steel`: Heat tint on steel: straw, bronze, purple and blue bands beside weld lines.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 1 | Thickness layout: 0 swirls of warped noise, 1 bands thinning away from weld lines. |
| `film_min` | float | 120 | 0 to 1200 | Thinnest film in nanometres. |
| `film_max` | float | 900 | 50 to 1600 | Thickest film in nanometres. |
| `scale` | int | 3 | 1 to 10 | Swirls or bands across the tile. |
| `swirl` | float | 0.6 | 0 to 1 | Domain warping of the film into marbled swirls. |
| `coverage` | float | 0.55 | 0.05 to 1 | Share of the surface under liquid (asphalt and water bases); 1 covers it all. |
| `vividness` | float | 1 | 0.3 to 3 | Strength of the interference colours. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`oil_slick_iridescent.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python oil_slick_iridescent.py --size 1024 --seed 7 --preset harbour_water --out textures/oil_slick_iridescent
python oil_slick_iridescent.py --width 512 --height 256 --set pattern=1 --orm --out maps
```

`--orm` also writes `oil_slick_iridescent_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import oil_slick_iridescent

maps = oil_slick_iridescent.generate(512, 512, seed=3, preset="harbour_water")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 20.4 s (13.1 s to compute, 7.4 s to write the PNG files) with a peak of about 680 MB; 256 x 256 takes about 1.38 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/oil_slick_iridescent/` of your project (for example `python oil_slick_iridescent.py --size 1024 --out path/to/project/baltor/textures/oil_slick_iridescent`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Two-beam interference at normal incidence: colours do not shift with viewing angle, multiple reflections and absorption are ignored, and a metal substrate is approximated by a negative real reflection amplitude instead of a complex index, so temper colours are close but not exact. The colour-matching functions are an analytic Gaussian fit and the grey part of the film reflectance is partly removed for clearer hues, so this is a stylized rendering of thin-film colour rather than a spectral measurement. Film thickness comes from noise or bands, not from flow or oxidation physics. One still frame.
