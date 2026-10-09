# Ocean wave normals from a directional wave spectrum

An open wind sea, a long parallel swell, short steep chop with whitecaps, a near-breaking storm sea or small isotropic ripples on a lake. Every component is a sine wave with a whole number of cycles across the tile in each direction, so the surface repeats exactly. Components are drawn from a directional spectrum, a log-normal band around `peak_waves` times a cosine-power spreading around `wind_angle`, by weighted sampling without replacement, and their amplitudes fall with the wavenumber.

Each wave is evaluated separably from per-column and per-row sine tables. `choppiness` moves the surface toward the crests the way Gerstner waves do: the height is resampled at the position minus the horizontal displacement of the same waves, scaled from the steepest compression so crests sharpen without folding. Where that compression is strongest, foam appears in the albedo and roughness and lifts the height a little. The normal map is the main product; albedo tints thin crests lighter, and roughness stays low except on foam.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `ocean_wave_normals_albedo.png` | 3 | sRGB | glTF base colour, values 0.01 to 0.95 |
| `normal` | `ocean_wave_normals_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `ocean_wave_normals_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.02 to 0.9 |
| `height` | `ocean_wave_normals_height.png` | 1 | linear | white is high |
| `ao` | `ocean_wave_normals_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Open sea: a moderate wind sea with sharpened crests and a little foam.
- `calm_swell`: Long parallel swell with smooth crests and no foam.
- `choppy_wind`: Short, steep wind chop from many directions with whitecaps.
- `stormy`: Heavy grey-green storm sea, near-breaking crests streaked with foam.
- `lake_ripples`: Small isotropic ripples on a brown-green lake.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `peak_waves` | int | 4 | 1 to 16 | Cycles of the dominant wavelength across the tile. |
| `components` | int | 48 | 8 to 96 | Number of sine waves summed. |
| `wind_angle` | float | 0.1 | 0 to 1 | Direction the waves travel, in turns from the +U axis. |
| `spread` | float | 0.45 | 0 to 1 | Directional spreading: 0 long parallel crests, 1 waves from every direction. |
| `detail` | float | 0.5 | 0 to 1 | Weight of short waves and ripples against the peak band. |
| `choppiness` | float | 0.4 | 0 to 1 | Sideways crest sharpening, 0 smooth sines to 1 nearly breaking. |
| `foam` | float | 0.2 | 0 to 1 | Whitecap foam on the most compressed crests. |
| `relief` | float | 1 | 0.2 to 2.5 | Strength of the normal map relief. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`ocean_wave_normals.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python ocean_wave_normals.py --size 1024 --seed 7 --preset calm_swell --out textures/ocean_wave_normals
python ocean_wave_normals.py --width 512 --height 256 --set peak_waves=16 --orm --out maps
```

`--orm` also writes `ocean_wave_normals_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import ocean_wave_normals

maps = ocean_wave_normals.generate(512, 512, seed=3, preset="calm_swell")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.4 s (15.8 s to compute, 9.6 s to write the PNG files) with a peak of about 653 MB; 256 x 256 takes about 1.67 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/ocean_wave_normals/` of your project (for example `python ocean_wave_normals.py --size 1024 --out path/to/project/baltor/textures/ocean_wave_normals`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.03, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

For a water shader, scroll two copies of the normal map at different scales and directions and blend them; the height map can drive vertex displacement on a subdivided plane.

## Limits

One still frame of a stylized spectrum, not an ocean simulation: there is no dispersion relation, time animation or FFT, and the spectrum shape is a log-normal band with cosine spreading rather than a measured model such as JONSWAP. Choppiness resamples the height once at the displaced position, an approximation of Gerstner waves that holds while crests do not fold. Every wave repeats across the tile, so long views show the repeat; blend two scales of the tile in the shader to hide it. Foam is placed from crest compression and noise, not from breaking physics, and the occlusion map is a mild stand-in.
