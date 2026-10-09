# Pixel-art stone brick wall with bevels and moss

Grey castle stone, sandstone blocks, a mossy cracked ruin or small red bricks in a regular running bond, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Courses split the height at whole art pixels; each course is cut into bricks at jittered positions with its own offset, so the joints stagger and the layout wraps around the tile.

Mortar is the top row of each course and the left column of each brick, which keeps exactly one mortar line between neighbours across the tile edges. Inside each brick the first row and column take the highlight colour and the last row and column the shadow colour. Stone grain is posterized noise with a Bayer dither, cracks are short random walks, and moss grows from the joints where a noise field allows it.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_stone_bricks_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_stone_bricks_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_stone_bricks_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `pixel_stone_bricks_height.png` | 1 | linear | white is high |
| `ao` | `pixel_stone_bricks_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey castle stone in staggered courses with a little moss.
- `sandstone`: Warm sandstone blocks, three courses, crisp and clean.
- `mossy_ruin`: Old green-grey ruin stones, cracked and overgrown.
- `red_brick`: Small red bricks in a regular running bond with pale mortar.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `courses` | int | 4 | 2 to 8 | Brick courses across the tile height. |
| `bricks_per_course` | int | 2 | 1 to 6 | Bricks in each course across the tile width. |
| `irregularity` | float | 0.4 | 0 to 1 | Random variation of brick lengths and course offsets (0 is a regular running bond). |
| `cracks` | float | 0.25 | 0 to 1 | Share of bricks with a crack. |
| `moss` | float | 0.15 | 0 to 1 | Moss growing from the joints. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_stone_bricks.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_stone_bricks.py --size 1024 --seed 7 --preset sandstone --out textures/pixel_stone_bricks
python pixel_stone_bricks.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_stone_bricks_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_stone_bricks

maps = pixel_stone_bricks.generate(512, 512, seed=3, preset="sandstone")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 8.9 s (0.9 s to compute, 8 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.65 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_stone_bricks/` of your project (for example `python pixel_stone_bricks.py --size 1024 --out path/to/project/baltor/textures/pixel_stone_bricks`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

Stylized pixel art with a fixed light from the top left baked into the bevel colours; roughness and height are values per drawn class, and the normal map treats each art pixel as a flat facet. Bricks are rectangles cut at whole art pixels; there are no corner pieces, arches or openings. Courses are limited to a quarter of the art size so every brick keeps a face pixel. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
