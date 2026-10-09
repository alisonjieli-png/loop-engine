# Pixel-art roof tiles in overlapping courses

Terracotta fish-scale tiles, blue-grey slate, green copper scales with pointed ends or wooden shingles with moss, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Courses are laid from the eaves upward: every tile reaches down past its course by `overlap`, so each higher course lies on the one below, and every other course shifts by half a tile.

Because the last course lies on the first course of the next repeat, the first course is painted first, then the others from the bottom up, and finally the ends of the first course again. Tile ends are square, round or pointed (`end_shape`); the pixels just below an end take a cast shadow, the end is outlined, the first column of a tile is a dark gap and the next a lit edge. `grain` adds wood grain and random widths for shingles, and `moss` grows in the shadows.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_roof_tiles_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_roof_tiles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_roof_tiles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.2 to 1 |
| `height` | `pixel_roof_tiles_height.png` | 1 | linear | white is high |
| `ao` | `pixel_roof_tiles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Terracotta fish-scale roof tiles with round ends.
- `blue_slate`: Blue-grey slate in square-ended courses.
- `verdigris_scales`: Green copper scales with pointed ends.
- `wooden_shingles`: Brown wooden shingles of random widths with grain and moss.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `course_pairs` | int | 2 | 1 to 4 | Pairs of tile courses down the tile (the course count is twice this, so the offset repeats). |
| `tiles_per_course` | int | 4 | 2 to 8 | Roof tiles across the tile width in each course. |
| `end_shape` | int | 1 | 0 to 2 | Tile end: 0 square, 1 round (fish scale), 2 pointed. |
| `overlap` | float | 0.45 | 0.2 to 0.7 | How far each tile reaches over the course below, as a share of the course height. |
| `grain` | int | 0 | 0 to 1 | 1 draws wood grain lines and gives the tiles random widths (shingles and shakes). |
| `moss` | float | 0 | 0 to 1 | Moss growing in the shadowed overlaps. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_roof_tiles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_roof_tiles.py --size 1024 --seed 7 --preset blue_slate --out textures/pixel_roof_tiles
python pixel_roof_tiles.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_roof_tiles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_roof_tiles

maps = pixel_roof_tiles.generate(512, 512, seed=3, preset="blue_slate")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 8.6 s (1.2 s to compute, 7.4 s to write the PNG files) with a peak of about 87 MB; 256 x 256 takes about 0.55 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_roof_tiles/` of your project (for example `python pixel_roof_tiles.py --size 1024 --out path/to/project/baltor/textures/pixel_roof_tiles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

Stylized pixel art with the light from the top left baked into the tile edges and shadows; it shows a flat roof plane, with no ridges, valleys, hips or eaves. Every other course shifts by half a tile, so the course count is even. Tile ends are three fixed shapes, and wooden shingles vary only in width. Roughness and height are values per drawn class, and the normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
