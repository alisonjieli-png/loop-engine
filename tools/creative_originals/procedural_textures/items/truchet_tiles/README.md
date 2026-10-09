# Truchet tiles: arcs, mazes and split triangles

Glazed ceramic with cobalt arcs raised over white and pale blue regions, a random diagonal maze printed on paper, brass arcs inlaid flush in dark walnut, or a cement floor of terracotta and cream half-square triangles. Each cell of the grid takes one of two turns from a hash of its index, or, with `order`, from the parity of its position, and the same few designs, turned, join across every edge into long meandering paths.

Quarter-circle tiles hold two arcs of radius one half around opposite corners; the regions between arcs are coloured by the parity of the grid corner each touches, which agrees across every cell edge, so the fill is a true two-colouring. Lines are drawn from their exact distance in cell units with a rounded profile and can be raised, printed flat or sunk as inlay and grout; `metal_lines` makes them metallic.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `truchet_tiles_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.95 |
| `normal` | `truchet_tiles_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `truchet_tiles_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `truchet_tiles_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `truchet_tiles_height.png` | 1 | linear | white is high |
| `ao` | `truchet_tiles_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Glazed ceramic: cobalt arcs raised over white and pale blue regions.
- `maze_print`: Random diagonal maze printed in black on off-white paper.
- `brass_inlay`: Brass arcs inlaid flush in dark walnut with alternating stained regions.
- `triangle_floor`: Cement floor of terracotta and cream half-square triangles.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `style` | int | 0 | 0 to 2 | 0 quarter-circle arcs, 1 diagonal maze, 2 split triangles. |
| `cells` | int | 8 | 2 to 32 | Tiles across the tile. |
| `line_width` | float | 0.16 | 0.02 to 0.45 | Width of the arcs or lines as a share of a cell. |
| `order` | float | 0 | 0 to 1 | Share of cells whose turn follows the checkerboard parity instead of chance. |
| `fill` | float | 0.8 | 0 to 1 | Contrast of the two-colour region fill (arcs and triangles). |
| `relief` | float | 0.6 | 0 to 1 | How far the lines stand above the ground (sunk below it for inlay and grout presets). |
| `metal_lines` | float | 0 | 0 to 1 | Metallic value of the lines, 1 for metal inlay. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`truchet_tiles.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python truchet_tiles.py --size 1024 --seed 7 --preset maze_print --out textures/truchet_tiles
python truchet_tiles.py --width 512 --height 256 --set style=2 --orm --out maps
```

`--orm` also writes `truchet_tiles_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import truchet_tiles

maps = truchet_tiles.generate(512, 512, seed=3, preset="maze_print")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.1 s (9.7 s to compute, 15.4 s to write the PNG files) with a peak of about 520 MB; 256 x 256 takes about 1.52 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/truchet_tiles/` of your project (for example `python truchet_tiles.py --size 1024 --out path/to/project/baltor/textures/truchet_tiles`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Three classic tile sets on a square grid; there are no multi-scale or winged tiles, and the diagonal maze has no region fill because its regions are not two-coloured by corner parity. Line relief is a rounded profile from the exact distance, with no bevel lighting or glaze pooling. The wood and cement grounds are light noise, not full wood or stone generators. Occlusion is a blurred-height estimate.
