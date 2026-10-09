# Pixel-art lava flow with glowing cracks

Black basalt plates over orange cracks, grey cooling crust with thin red cracks, a bubbling lava lake or fantasy green magma, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. Crust plates are the cells of a Voronoi diagram; the distance to the border in art pixels decides what is molten: a pale core along the middle of each crack, orange around it and a dithered band of dull red on the plate rims.

`crust` below 1 shrinks the plates to islands around their seed points and opens a lava lake in which `bubbles` draws dark rings around bright pixels. On the crust, pixels with molten neighbours to the left or above take the plate's lit edge colour and those with molten neighbours to the right or below its shadow, so each plate reads as a raised slab. The emissive map holds the glow alone.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_lava_flow_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.98 |
| `normal` | `pixel_lava_flow_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_lava_flow_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.25 to 1 |
| `height` | `pixel_lava_flow_height.png` | 1 | linear | white is high |
| `ao` | `pixel_lava_flow_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `pixel_lava_flow_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Black basalt plates over bright orange cracks.
- `cooling`: Grey cooling crust with thin dull-red cracks.
- `lava_lake`: A bubbling orange lake with small floating crust islands.
- `toxic_magma`: Fantasy green-yellow magma under violet crust.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `plates` | int | 3 | 2 to 8 | Crust plates across the tile. |
| `crack_width` | float | 0.9 | 0.5 to 3 | Half width of the molten cracks in art pixels. |
| `crust` | float | 1 | 0.2 to 1 | Plate size: 1 fills the cells up to the cracks, lower values leave islands in a lava lake. |
| `bubbles` | float | 0 | 0 to 1 | Density of bubbles in wide molten areas. |
| `hot_spots` | float | 0.2 | 0 to 1 | Glowing specks on the crust. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the glow in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_lava_flow.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_lava_flow.py --size 1024 --seed 7 --preset cooling --out textures/pixel_lava_flow
python pixel_lava_flow.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_lava_flow_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_lava_flow

maps = pixel_lava_flow.generate(512, 512, seed=3, preset="cooling")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 9.7 s (1 s to compute, 8.7 s to write the PNG files) with a peak of about 114 MB; 256 x 256 takes about 0.83 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_lava_flow/` of your project (for example `python pixel_lava_flow.py --size 1024 --out path/to/project/baltor/textures/pixel_lava_flow`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.005, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; the emissive PNG can drive a glow layer or an additive sprite. `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

A still frame of stylized pixel art, not a flow simulation, and it does not animate; for motion, cycle seeds or shift the emissive strength. The glow is a fixed three-step colour scale of distance to the plate border, not a temperature model, and the albedo also holds the glowing colours so the tile reads without lighting. Plates are Voronoi cells. Emission strength is set in the engine; the map holds colour only. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
