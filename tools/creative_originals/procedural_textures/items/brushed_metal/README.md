# Brushed metal in five alloys

Stainless steel, bright aluminium, brass, copper or satin titanium. Brushing leaves countless parallel micro-grooves; here they are noise stretched hundreds of times along the brushing direction, at two scales, slightly waved so the lines never look ruled. Broader bands (`banding`), where the abrasive pressed harder or softer on a pass, vary brightness and roughness at a scale that stays visible from a distance.

A few deeper scratches run the same way, and faint smudges like fingerprints and wiping marks vary the roughness. The whole surface is metal, so the metallic map is uniform and the base colour is the metal's reflectance.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `brushed_metal_albedo.png` | 3 | sRGB | glTF base colour, values 0.3 to 0.98 |
| `normal` | `brushed_metal_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `brushed_metal_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 0.9 |
| `metallic` | `brushed_metal_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `brushed_metal_height.png` | 1 | linear | white is high |
| `ao` | `brushed_metal_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Brushed stainless steel.
- `aluminium`: Bright brushed aluminium, slightly finer.
- `brass`: Brushed brass with soft smudges.
- `copper`: Brushed copper with coarse grooves.
- `titanium_satin`: Satin titanium, fine and smooth, few scratches.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `streak_density` | int | 220 | 40 to 600 | Streak cells across the tile height (higher gives finer lines). |
| `streak_depth` | float | 0.5 | 0 to 1 | Depth of the brushing grooves. |
| `waviness` | float | 0.3 | 0 to 1 | How much the streaks wave. |
| `scratches` | int | 12 | 0 to 120 | Deeper scratches along the brushing direction. |
| `roughness_base` | float | 0.32 | 0.05 to 0.8 | Average roughness. |
| `smudges` | float | 0.3 | 0 to 1 | Faint blotches of different roughness, like fingerprints and wiping marks. |
| `banding` | float | 0.6 | 0 to 1 | Broad bands along the brushing direction from uneven abrasive passes. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier (metals keep at most their reflectance). |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`brushed_metal.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python brushed_metal.py --size 1024 --seed 7 --preset aluminium --out textures/brushed_metal
python brushed_metal.py --width 512 --height 256 --set streak_density=600 --orm --out maps
```

`--orm` also writes `brushed_metal_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import brushed_metal

maps = brushed_metal.generate(512, 512, seed=3, preset="aluminium")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 14.9 s (8.4 s to compute, 6.5 s to write the PNG files) with a peak of about 656 MB; 256 x 256 takes about 1.03 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/brushed_metal/` of your project (for example `python brushed_metal.py --size 1024 --out path/to/project/baltor/textures/brushed_metal`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.8) and the height map through a Displacement node (scale 0.001, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Brushing runs across the tile width only; rotate the UVs for other directions. The grooves live in the normal and roughness maps, which carry no anisotropy direction, so the stretched highlight of real brushed metal needs an anisotropic shader on top. Metal colours are approximate reflectances. Occlusion is a blurred-height estimate, not ray traced.
