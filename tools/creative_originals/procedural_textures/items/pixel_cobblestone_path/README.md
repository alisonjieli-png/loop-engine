# Pixel-art cobblestone path with grass joints

Grey round cobbles with grass, warm square sandstone setts, dark wet cobbles at night or an old mossy path, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Stones sit on a jittered grid; with an even row count every other row shifts by half a stone, as setts are laid.

Each stone is a superellipse whose exponent blends from a square sett (`roundness` 0) to a round cobble (1), and a pixel belongs to the stone it falls deepest inside among the nine nearest, so neighbours never overlap. The offset from the stone centre along a light from the top left picks highlight, light, base or shadow, the outer ring is a dark outline, and wet stones add a white glint. Grass with light tufts or packed dirt fills the joints.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_cobblestone_path_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_cobblestone_path_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_cobblestone_path_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `height` | `pixel_cobblestone_path_height.png` | 1 | linear | white is high |
| `ao` | `pixel_cobblestone_path_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey round cobbles with grass growing between them.
- `sandstone_setts`: Warm square sandstone setts in offset rows with sandy joints.
- `wet_night`: Dark wet cobbles with glints and muddy joints.
- `mossy_path`: Old green-grey cobbles sunk in moss.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `stones` | int | 4 | 2 to 8 | Stones across the tile (and rows down it). |
| `roundness` | float | 0.8 | 0 to 1 | Stone shape: 0 square setts, 1 round cobbles. |
| `stone_size` | float | 1 | 0.6 to 1.2 | Stone size as a share of its cell; neighbours never overlap, larger values close the joints. |
| `jitter` | float | 0.5 | 0 to 1 | Random offset and size variation of the stones. |
| `grass` | float | 0.7 | 0 to 1 | Share of the joints grown with grass instead of bare dirt. |
| `wet` | float | 0 | 0 to 1 | Wetness: lower roughness and glints on the stones. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_cobblestone_path.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_cobblestone_path.py --size 1024 --seed 7 --preset sandstone_setts --out textures/pixel_cobblestone_path
python pixel_cobblestone_path.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_cobblestone_path_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_cobblestone_path

maps = pixel_cobblestone_path.generate(512, 512, seed=3, preset="sandstone_setts")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 6.8 s (0.7 s to compute, 6.2 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.54 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_cobblestone_path/` of your project (for example `python pixel_cobblestone_path.py --size 1024 --out path/to/project/baltor/textures/pixel_cobblestone_path`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

Stylized pixel art with the light from the top left baked into the stone shading. Stones sit on a jittered grid, one per cell, so the layout stays orderly; there are no curved courses or fan patterns. Shapes are superellipses with a dome height. Wetness lowers roughness and adds glints but draws no puddles or reflections. The normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
