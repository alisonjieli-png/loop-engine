# Pixel-art dungeon floor of irregular stone slabs

A grey dungeon floor, a mossy crypt, a sandstone temple or a flooded cellar, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. The floor is random ashlar: a coarse grid of `cells` on the torus is filled greedily with slabs one or two cells wide and tall, so long joint lines break wherever a large slab spans them.

Every slab owns the joint on its top and left edge, which keeps exactly one dark joint between neighbours across the tile edges; its next row and column are a lit bevel, its last row and column a shadow bevel, and corners are chipped into the joint at random. Faces are posterized noise with a tone per slab, cracks are branching random walks, moss grows in the joints and spills onto the edges, and `puddles` adds glossy standing water with highlights.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_dungeon_floor_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `pixel_dungeon_floor_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_dungeon_floor_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 1 |
| `height` | `pixel_dungeon_floor_height.png` | 1 | linear | white is high |
| `ao` | `pixel_dungeon_floor_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey dungeon slabs with cracks, chipped corners and a little moss.
- `mossy_crypt`: Green-grey crypt floor overgrown with moss in every joint.
- `sandstone_temple`: Warm sandstone temple slabs, large and tidy.
- `flooded_cellar`: Dark cellar flagstones with glossy puddles.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `cells` | int | 4 | 2 to 8 | Layout cells across the tile; slabs span one or two cells each way. |
| `large_slabs` | float | 0.5 | 0 to 1 | Chance that a slab spans two cells (0 is a square grid of slabs). |
| `cracks` | float | 0.4 | 0 to 1 | Share of slabs with a crack. |
| `chips` | float | 0.4 | 0 to 1 | Chance that a slab corner is chipped. |
| `moss` | float | 0.2 | 0 to 1 | Moss in the joints. |
| `puddles` | float | 0 | 0 to 1 | Coverage of standing water. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_dungeon_floor.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_dungeon_floor.py --size 1024 --seed 7 --preset mossy_crypt --out textures/pixel_dungeon_floor
python pixel_dungeon_floor.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_dungeon_floor_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_dungeon_floor

maps = pixel_dungeon_floor.generate(512, 512, seed=3, preset="mossy_crypt")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 6.8 s (0.7 s to compute, 6.1 s to write the PNG files) with a peak of about 88 MB; 256 x 256 takes about 0.47 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_dungeon_floor/` of your project (for example `python pixel_dungeon_floor.py --size 1024 --out path/to/project/baltor/textures/pixel_dungeon_floor`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

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

Stylized pixel art with the light from the top left baked into the slab bevels. Slabs are rectangles on a coarse grid of cells, one or two cells each way, so the layout has no curved or diagonal joints, and a grid of two cells makes plain square slabs. Cracks are random walks and puddles thresholded noise. Roughness and height are values per drawn class, and the normal map treats each art pixel as a flat facet. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
