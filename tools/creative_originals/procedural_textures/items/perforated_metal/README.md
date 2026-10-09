# Perforated metal sheet with alpha holes

Stainless sheet with staggered round holes, black painted sheet with square holes, an aluminium slotted grille, a fine hexagonal speaker mesh or brass with round holes in straight rows. Holes sit on a whole-number lattice so the sheet repeats: staggered round holes use a hexagonal lattice, the others a square grid.

Each hole outline is a distance function in the hole's own coordinates (circle, rounded square, stadium slot or hexagon); the albedo alpha is 0 inside and 1 on the metal, anti-aliased over a pixel, and `open_area` sets the share of open sheet. A punching burr lifts a thin ring around every hole, the sheet keeps a rolled grain, and paint, where present, is a dielectric.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `perforated_metal_albedo.png` | 4 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `perforated_metal_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `perforated_metal_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `perforated_metal_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `perforated_metal_height.png` | 1 | linear | white is high |
| `ao` | `perforated_metal_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Stainless sheet with staggered round holes.
- `square_black`: Black painted sheet with square holes.
- `slotted_grille`: Aluminium grille with long slots.
- `hex_speaker`: Fine hexagonal speaker mesh in dark grey paint.
- `straight_round_brass`: Brass sheet with round holes in straight rows.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 4 | Holes: 0 staggered round, 1 straight round, 2 square, 3 slots, 4 hexagonal. |
| `holes_across` | int | 10 | 3 to 48 | Holes across the tile. |
| `open_area` | float | 0.55 | 0.15 to 0.85 | Hole size relative to the hole spacing. |
| `burr` | float | 0.4 | 0 to 1 | Raised punching burr around each hole. |
| `paint` | float | 0 | 0 to 1 | Paint coverage (0 bare metal, 1 painted). |
| `grime` | float | 0.15 | 0 to 1 | Dirt and fingerprints on the sheet. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`perforated_metal.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python perforated_metal.py --size 1024 --seed 7 --preset square_black --out textures/perforated_metal
python perforated_metal.py --width 512 --height 256 --set pattern=4 --orm --out maps
```

`--orm` also writes `perforated_metal_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import perforated_metal

maps = perforated_metal.generate(512, 512, seed=3, preset="square_black")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 19.1 s (8.8 s to compute, 10.3 s to write the PNG files) with a peak of about 604 MB; 256 x 256 takes about 1.38 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/perforated_metal/` of your project (for example `python perforated_metal.py --size 1024 --out path/to/project/baltor/textures/perforated_metal`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses an alpha scissor at 0.5.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `alphaTest: 0.5`.

## Limits

Holes are cut through the albedo alpha, so the material needs alpha scissor or blending, and the hole walls have no thickness. Burrs are a thin height ring. The lattice runs edge to edge; real sheets keep solid margins this tile lacks. Occlusion is a blurred-height estimate, not ray traced.
