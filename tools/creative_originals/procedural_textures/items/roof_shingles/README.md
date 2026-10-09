# Staggered roof shingles: slate, asphalt or cedar

Blue-grey slate, charcoal asphalt tabs, weathered cedar shakes, two-tone Victorian fish scale or green slate with pointed butts. The slope runs down the tile: `rows` rows of `per_row` shingles, each row offset by half a shingle (or randomly when `width_variation` makes the widths uneven), so the roof repeats in both directions.

Each row's shingles end at its butt line and reach up under the rows above, and each row lies on top of the one below, as shingles laid from the eaves upward do. A pixel belongs to the first row from its butt line downward whose shingle covers it: `butt` cuts the lower edge square, round or pointed, and `keyway` leaves narrow slots through which the darker shingle beneath shows. `material` sets the surface (cleft slate, mineral granules or split grain), `thickness` the step at each butt and its cast shadow, and `weathering` adds streaks, lichen and moss.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `roof_shingles_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `roof_shingles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `roof_shingles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.35 to 1 |
| `height` | `roof_shingles_height.png` | 1 | linear | white is high |
| `ao` | `roof_shingles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Blue-grey natural slate with square butts in staggered rows.
- `asphalt_charcoal`: Charcoal and brown asphalt tabs with granules and wide keyways.
- `cedar_shakes`: Weathered cedar shakes of random widths with split grain and moss.
- `fishscale_slate`: Victorian fish-scale slate with round butts in two tones.
- `pointed_green`: Green-grey slate with pointed butts, a decorative diamond course look.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `material` | int | 0 | 0 to 2 | 0 natural slate (cleft layers), 1 asphalt (mineral granules), 2 cedar shakes (split wood grain). |
| `butt` | int | 0 | 0 to 2 | Shape of the exposed lower edge: 0 square, 1 round (fish scale), 2 pointed. |
| `rows` | int | 8 | 3 to 20 | Rows of shingles down the tile height. |
| `per_row` | int | 5 | 2 to 14 | Shingles across the tile width in each row. |
| `width_variation` | float | 0 | 0 to 1 | Random shingle widths and row offsets, as split shakes have; 0 keeps equal widths offset by half. |
| `keyway` | float | 0.03 | 0 to 0.12 | Gap between neighbouring shingles in a row, as a share of the mean shingle width. |
| `thickness` | float | 0.5 | 0.1 to 1 | Height of the step at each butt. |
| `weathering` | float | 0.25 | 0 to 1 | Fading, streaks, lichen and moss. |
| `colour_variation` | float | 0.4 | 0 to 1 | Spread of colour between shingles. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`roof_shingles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python roof_shingles.py --size 1024 --seed 7 --preset asphalt_charcoal --out textures/roof_shingles
python roof_shingles.py --width 512 --height 256 --set material=2 --orm --out maps
```

`--orm` also writes `roof_shingles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import roof_shingles

maps = roof_shingles.generate(512, 512, seed=3, preset="asphalt_charcoal")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 24.1 s (12.8 s to compute, 11.3 s to write the PNG files) with a peak of about 599 MB; 256 x 256 takes about 1.8 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/roof_shingles/` of your project (for example `python roof_shingles.py --size 1024 --out path/to/project/baltor/textures/roof_shingles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 2). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.025, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

The slope always runs down the tile height. Shingles are flat pieces whose thickness shows only as a step in height and a darker band; there are no nail heads, ridges, valleys, flashing or architectural laminated shingles. Shadows under the butts are tinted into the albedo, so they read as baked under strong side light. Granules, cleft layers, grain, lichen and moss are noise approximations. Occlusion is a blurred-height estimate, not ray traced.
