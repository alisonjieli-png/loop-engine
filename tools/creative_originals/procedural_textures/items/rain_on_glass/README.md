# Rain on glass: droplets, running trails and mist

Steady rain with mixed droplets and a few trails, fine drizzle, a downpour of large merging drops and long trails, or a misted window wiped into clear streaks by running drops. Droplets come in three size classes, each jittered inside the cells of its own grid with a chance per cell, so small drops are many and large ones few. Each is a flattened dome painted into the height field with a maximum, so touching drops merge.

Running drops leave trails: a path that wanders across the width as it runs down, painted as a thin wet streak, with the running drop at its lower end and small beads left behind. Mist is fractal noise wiped clear along trails and around large drops. The normal map carries the drop bulges for refraction; the albedo alpha is low on clear glass, higher on drops and highest on mist, and drop rims are darkened with a highlight on the side facing the upper left.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `rain_on_glass_albedo.png` | 4 | sRGB | glTF base colour, values 0.15 to 1 |
| `normal` | `rain_on_glass_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `rain_on_glass_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0 to 0.8 |
| `height` | `rain_on_glass_height.png` | 1 | linear | white is high |
| `ao` | `rain_on_glass_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Steady rain: mixed droplets and a few trails with beads.
- `drizzle`: Fine drizzle: many small drops and no trails.
- `downpour`: Downpour: large merging drops and many long trails.
- `misted`: Misted window: condensation wiped into clear streaks by running drops.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `drops` | float | 0.7 | 0 to 1 | Density of droplets. |
| `drop_size` | float | 1 | 0.5 to 2 | Size of droplets and trails. |
| `trails` | int | 5 | 0 to 30 | Running drops that leave trails down the glass. |
| `beading` | float | 0.5 | 0 to 1 | Beads left behind along the trails. |
| `mist` | float | 0 | 0 to 1 | Fine condensation misting the glass, wiped clear by trails and large drops. |
| `relief` | float | 1 | 0.3 to 2 | Strength of the drop bulges in the normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`rain_on_glass.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python rain_on_glass.py --size 1024 --seed 7 --preset drizzle --out textures/rain_on_glass
python rain_on_glass.py --width 512 --height 256 --set drops=1 --orm --out maps
```

`--orm` also writes `rain_on_glass_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import rain_on_glass

maps = rain_on_glass.generate(512, 512, seed=3, preset="drizzle")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 16.7 s (9.3 s to compute, 7.5 s to write the PNG files) with a peak of about 668 MB; 256 x 256 takes about 1.06 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/rain_on_glass/` of your project (for example `python rain_on_glass.py --size 1024 --out path/to/project/baltor/textures/rain_on_glass`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses alpha blending, so the material sorts with other transparent surfaces.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `transparent: true`.

For a refractive window, sample the scene behind the glass at the screen position offset by the normal map's red and green; the overlay alpha then adds rims, highlights and mist on top.

## Limits

A still frame: drops do not move, and trails run down the tile and wrap around it, so a repeating tile repeats its trails. Drops are domes of a fixed profile merged by taking the higher one, not a fluid simulation, and the lighting painted into the albedo assumes light from the upper left. Refraction needs a glass shader that offsets the background by the normal map; the albedo alone only darkens rims and lights one side. Drops smaller than half a pixel are drawn at that size with less height.
