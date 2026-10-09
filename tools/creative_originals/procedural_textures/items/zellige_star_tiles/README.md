# Zellige eight-point star and cross tiles

White stars with cobalt crosses, emerald stars with white crosses, honey terracotta with dark green, or a mixed souk palette. Stars sit on a square lattice, `stars_across` per tile, and every four stars enclose a cross with pointed arms, so the panel repeats in both directions.

Each star is an axis-aligned square united with the same square turned 45 degrees, sized so neighbouring stars meet tip to tip. A pixel takes the signed distance to the four stars at the corners of its lattice cell: inside one it belongs to that star, otherwise to the cell's cross. The distance shapes the grout and a steep cut edge (`edge_cut`), which `chipping` breaks down to the clay. `glaze_unevenness` makes the glaze thick and thin, darker where it pools, and `pinholes` adds small craters. `colour_mode` 0 colours stars and crosses from their own palettes; 1 lets every piece pick from both.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `zellige_star_tiles_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `zellige_star_tiles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `zellige_star_tiles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 1 |
| `height` | `zellige_star_tiles_height.png` | 1 | linear | white is high |
| `ao` | `zellige_star_tiles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White stars and cobalt blue crosses with glossy, uneven zellige glaze.
- `emerald_white`: Variegated emerald stars and white crosses, more stars per tile.
- `honey_terracotta`: Honey-glazed terracotta stars with dark green crosses and wider joints.
- `souk_mix`: Small pieces in a mixed palette of blue, green, ochre, white and black.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `stars_across` | int | 3 | 1 to 12 | Stars across the tile width; a cross sits between every four stars. |
| `colour_mode` | int | 0 | 0 to 1 | 0 stars take the star colours and crosses the cross colours, 1 every piece picks from both. |
| `grout_width` | float | 0.012 | 0.002 to 0.05 | Joint width in star spacings. |
| `grout_depth` | float | 0.4 | 0 to 1 | How far the grout sits below the glaze. |
| `edge_cut` | float | 0.018 | 0.004 to 0.06 | Width of the steep cut edge around each piece, in star spacings. |
| `glaze_unevenness` | float | 0.6 | 0 to 1 | Thick and thin glaze: bumps in the surface and darker pools where the glaze is thick. |
| `pinholes` | float | 0.3 | 0 to 1 | Small craters in the glaze. |
| `chipping` | float | 0.35 | 0 to 1 | Chipped edges that show the clay body. |
| `colour_variation` | float | 0.5 | 0 to 1 | Spread of tone between pieces of one colour. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`zellige_star_tiles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python zellige_star_tiles.py --size 1024 --seed 7 --preset emerald_white --out textures/zellige_star_tiles
python zellige_star_tiles.py --width 512 --height 256 --set stars_across=12 --orm --out maps
```

`--orm` also writes `zellige_star_tiles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import zellige_star_tiles

maps = zellige_star_tiles.generate(512, 512, seed=3, preset="emerald_white")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 30.7 s (20.7 s to compute, 10 s to write the PNG files) with a peak of about 694 MB; 256 x 256 takes about 2.19 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/zellige_star_tiles/` of your project (for example `python zellige_star_tiles.py --size 1024 --out path/to/project/baltor/textures/zellige_star_tiles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.01, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

One layout only: stars sized to meet tip to tip, so the crosses have pointed arms; other star proportions and larger girih patterns are out of scope. Glaze thickness, pinholes and chips are noise-driven approximations; the glaze is opaque colour with no depth or crazing. Colours are artistic. Occlusion is a blurred-height estimate, not ray traced.
