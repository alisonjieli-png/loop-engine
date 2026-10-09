# Pixel-art crystal cave wall with glowing gems

Violet amethyst, pale ice crystals, small emeralds or glowing red crystals in a dark cave wall, drawn on a small art grid (`art_pixels` square) and enlarged with nearest-neighbour sampling. The rock is a periodic height field lit from the top left: its slope along the light picks one of four rock tones, so the wall reads as lumpy stone.

Crystal clusters sit at Poisson-disc points; each holds `crystals` pencil-shaped polygons leaning out from the cluster's foot. A pixel inside a crystal is shaded by the side of the crystal axis it lies on, the lit edge takes the highlight, the tip a glint and the outer ring a dark outline. Rock beside a crystal takes a solid glow ring and a dithered outer ring set by `glow`. The emissive map holds the crystals and their halo.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `pixel_crystal_cave_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.98 |
| `normal` | `pixel_crystal_cave_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `pixel_crystal_cave_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `height` | `pixel_crystal_cave_height.png` | 1 | linear | white is high |
| `ao` | `pixel_crystal_cave_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `pixel_crystal_cave_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Amethyst clusters glowing violet in dark purple-grey rock.
- `ice_blue`: Long pale-blue ice crystals in cold blue-grey rock.
- `emerald`: Short green emeralds scattered in brown-black rock.
- `fire_ruby`: Red-orange crystals with a strong warm glow in charred rock.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `art_pixels` | int | 32 | 16 to 64 | Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling. |
| `clusters` | float | 0.6 | 0 to 1 | Share of the evenly spread cluster positions that hold crystals. |
| `crystals` | int | 3 | 1 to 5 | Crystals in each cluster. |
| `crystal_length` | float | 7 | 3 to 12 | Typical crystal length in art pixels. |
| `glow` | float | 0.6 | 0 to 1 | Strength of the glow halo on the rock around the crystals. |
| `lumps` | int | 4 | 2 to 8 | Size of the rock lumps: noise cells across the tile. |
| `relief` | float | 1 | 0.2 to 2 | Strength of the per-pixel normal map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the glow in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`pixel_crystal_cave.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python pixel_crystal_cave.py --size 1024 --seed 7 --preset ice_blue --out textures/pixel_crystal_cave
python pixel_crystal_cave.py --width 512 --height 256 --set art_pixels=64 --orm --out maps
```

`--orm` also writes `pixel_crystal_cave_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import pixel_crystal_cave

maps = pixel_crystal_cave.generate(512, 512, seed=3, preset="ice_blue")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 9.3 s (0.9 s to compute, 8.4 s to write the PNG files) with a peak of about 114 MB; 256 x 256 takes about 0.59 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/pixel_crystal_cave/` of your project (for example `python pixel_crystal_cave.py --size 1024 --out path/to/project/baltor/textures/pixel_crystal_cave`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Texture filtering is nearest with mipmaps, which keeps pixel edges sharp.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.006, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

For Godot 2D, load the albedo and normal PNGs into a CanvasTexture (diffuse and normal textures) and set the texture filter to nearest; the emissive PNG can drive a glow layer. `material.tres` is a StandardMaterial3D for putting the tile on 3D surfaces. Choose an output size that is a whole multiple of `art_pixels` (for example `--size 256` with 32 art pixels) so every art pixel covers the same number of output pixels; `--size 32` writes one output pixel per art pixel.

## Limits

A still frame of stylized pixel art; the glow does not pulse or light the scene. The light from the top left is baked into the rock tones and crystal faces. Crystals are flat five-sided polygons with two faces, not modelled prisms, and on a 16-pixel grid they shrink to a few pixels. Rock lumps come from fractal noise. Emission strength is set in the engine; the map holds colour only. Output sizes that are not a whole multiple of art_pixels give art pixels of unequal widths. Occlusion is a blurred-height estimate posterized to eighths.
