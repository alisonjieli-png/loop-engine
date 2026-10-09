# Hexagonal ceramic tiles with lattice colour patterns

White wall hexagons with grey accents, white floor hexagons with black flowers, large terracotta pavers, mint and white rows or a blue blend. The tile holds `columns` pointy-top hexagons across and the even row count closest to a regular lattice, so the pattern repeats in both directions.

Each pixel finds its hexagon among the centres of the two nearest rows and measures the distance to the cell border. That distance sets the grout, the rounded edge (`bevel`) and a glaze that domes toward the centre (`pillow`) and pools darker at the edge. `pattern` chooses the colour rule: a random mix with `accent_share` accents, flowers of a centre and six petals scattered on the lattice, alternating rows, or clusters that drift between the palette colours. `chipping` breaks the edges down to the clay body.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `hexagon_tiles_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.92 |
| `normal` | `hexagon_tiles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `hexagon_tiles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 1 |
| `height` | `hexagon_tiles_height.png` | 1 | linear | white is high |
| `ao` | `hexagon_tiles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: White glossy hexagon wall tiles with a few pale grey accents and light grout.
- `black_white_flowers`: Small white hexagons with scattered flowers: six black petals around a grey centre.
- `terracotta_pavers`: Large matte terracotta hexagon pavers with wide sandy joints and worn, chipped edges.
- `mint_rows`: Glossy mint and white hexagons in alternating rows.
- `ocean_blend`: Small blue and teal hexagons drifting between shades in clusters.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `columns` | int | 7 | 3 to 26 | Hexagons across the tile width; the row count is the even number closest to a regular lattice. |
| `pattern` | int | 0 | 0 to 3 | Colour rule on the lattice: 0 random mix with accents, 1 scattered flowers (an accent centre with six petals), 2 alternating rows, 3 clustered blend that drifts between the palette colours. |
| `grout_width` | float | 0.05 | 0.01 to 0.2 | Joint width in hexagon widths (across the flats). |
| `grout_depth` | float | 0.5 | 0 to 1 | How far the grout sits below the tile faces: 0 flush, 1 deep. |
| `bevel` | float | 0.06 | 0.01 to 0.25 | Width of the rounded tile edge in hexagon widths. |
| `pillow` | float | 0.4 | 0 to 1 | Dome of the glaze toward the tile centre, as handmade and cushion-edged tiles have. |
| `glaze_waviness` | float | 0.4 | 0 to 1 | Low ripples in the glaze surface that break up reflections. |
| `chipping` | float | 0.15 | 0 to 1 | Chipped tile edges that expose the clay body, 0 none to 1 heavily damaged. |
| `accent_share` | float | 0.12 | 0 to 1 | Share of accent tiles in the random mix, or how densely flowers are scattered. |
| `colour_variation` | float | 0.4 | 0 to 1 | Spread of tone between tiles of one colour. |
| `dirt` | float | 0.2 | 0 to 1 | Grime in the grout and along the tile edges. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`hexagon_tiles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python hexagon_tiles.py --size 1024 --seed 7 --preset black_white_flowers --out textures/hexagon_tiles
python hexagon_tiles.py --width 512 --height 256 --set columns=26 --orm --out maps
```

`--orm` also writes `hexagon_tiles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import hexagon_tiles

maps = hexagon_tiles.generate(512, 512, seed=3, preset="black_white_flowers")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 26.4 s (15.5 s to compute, 10.9 s to write the PNG files) with a peak of about 598 MB; 256 x 256 takes about 1.99 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/hexagon_tiles/` of your project (for example `python hexagon_tiles.py --size 1024 --out path/to/project/baltor/textures/hexagon_tiles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.012, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

A square tile holds an even number of hexagon rows, so hexagons are squashed or stretched by up to 4 percent for 5 columns and about 1 percent for 7, 12, 14 or 19 columns (15 percent for 3, 4 or 6). Glaze is opaque colour with a low roughness; there is no crazing, transparency or depth in the glaze. Flowers are dropped greedily in a seeded order, so their spacing is irregular. Occlusion is a blurred-height estimate, not ray traced.
