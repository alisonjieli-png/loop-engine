# Lava crust with glowing cracks

An active flow, a cooling flow, blocky clinker or a lava lake. Plates are Voronoi cells drifting apart on the torus, and the gap between them is molten. Glow follows depth into the crack through a heat ramp from deep red through orange to a pale yellow core, and plate rims carry a dim halo.

Plate tops are rough basalt with ropy wrinkles. The emissive map holds the glow alone in sRGB; albedo stays dark where the lava glows so the engine adds light rather than reflecting it.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `lava_crust_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.5 |
| `normal` | `lava_crust_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `lava_crust_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `lava_crust_height.png` | 1 | linear | white is high |
| `ao` | `lava_crust_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `lava_crust_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Active flow: black crust plates over bright orange cracks.
- `cooling`: Cooling flow: thin dull-red cracks and grey crust.
- `clinker`: Blocky a'a clinker broken into many small glowing pieces.
- `lava_lake`: Wide molten seams between drifting rafts.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `plates_across` | int | 6 | 2 to 20 | Crust plates across the tile. |
| `crack_width` | float | 0.08 | 0.01 to 0.3 | Molten gap width in plate widths. |
| `heat` | float | 0.85 | 0.05 to 1 | Temperature of the melt: brightness and colour of the glow. |
| `rim_glow` | float | 0.4 | 0 to 1 | Heat halo creeping onto the plate rims. |
| `ropes` | float | 0.5 | 0 to 1 | Ropy wrinkles on the crust. |
| `fragmentation` | float | 0.2 | 0 to 1 | Secondary cracks breaking plates into clinker. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and glow in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`lava_crust.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python lava_crust.py --size 1024 --seed 7 --preset cooling --out textures/lava_crust
python lava_crust.py --width 512 --height 256 --set plates_across=20 --orm --out maps
```

`--orm` also writes `lava_crust_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import lava_crust

maps = lava_crust.generate(512, 512, seed=3, preset="cooling")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 24.7 s (13.6 s to compute, 11.1 s to write the PNG files) with a peak of about 795 MB; 256 x 256 takes about 1.7 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/lava_crust/` of your project (for example `python lava_crust.py --size 1024 --out path/to/project/baltor/textures/lava_crust`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion, emission and a height map for parallax (`heightmap_scale` 2). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.03, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

## Limits

The glow is a colour ramp of crack depth, not a blackbody or flow simulation, and it does not animate. Plates are Voronoi cells. Emission strength must be set in the engine; the map holds colour only. Occlusion is a blurred-height estimate.
