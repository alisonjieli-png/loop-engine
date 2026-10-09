# Galvanized steel spangle

Fresh galvanized sheet with large bright spangles, minimized spangle, weathered steel with white rust, or bold high-contrast crystals. Hot-dip zinc freezes into large flat crystals; each is a cell of a jittered Voronoi diagram with its own orientation, which sets how much light it sends back, so every cell takes its own brightness and roughness.

Inside a crystal, dendrites grow from the nucleus: stripes along the crystal's axis plus a herringbone of side branches, computed relative to the nucleus on the torus so crystals that cross the tile edge stay whole. Weathering (`white_rust`) adds dull white zinc corrosion, the only non-metal part.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `galvanized_spangle_albedo.png` | 3 | sRGB | glTF base colour, values 0.3 to 0.95 |
| `normal` | `galvanized_spangle_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `galvanized_spangle_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `galvanized_spangle_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `galvanized_spangle_height.png` | 1 | linear | white is high |
| `ao` | `galvanized_spangle_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Fresh galvanized sheet with large bright spangles.
- `minimized`: Minimized spangle: small, low-contrast crystals.
- `weathered`: Old galvanized steel, dull with white rust.
- `bold_spangle`: Very large, high-contrast crystals with strong feathering.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `crystals_across` | int | 5 | 2 to 24 | Spangle crystals across the tile. |
| `contrast` | float | 0.5 | 0 to 1 | Brightness difference between crystals. |
| `dendrites` | float | 0.5 | 0 to 1 | Visibility of the feathered dendrite pattern inside crystals. |
| `white_rust` | float | 0 | 0 to 1 | Dull white zinc corrosion. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`galvanized_spangle.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python galvanized_spangle.py --size 1024 --seed 7 --preset minimized --out textures/galvanized_spangle
python galvanized_spangle.py --width 512 --height 256 --set crystals_across=24 --orm --out maps
```

`--orm` also writes `galvanized_spangle_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import galvanized_spangle

maps = galvanized_spangle.generate(512, 512, seed=3, preset="minimized")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 28.9 s (12.4 s to compute, 16.5 s to write the PNG files) with a peak of about 689 MB; 256 x 256 takes about 2.22 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/galvanized_spangle/` of your project (for example `python galvanized_spangle.py --size 1024 --out path/to/project/baltor/textures/galvanized_spangle`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.8) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Each crystal's brightness is baked into albedo and roughness; real spangle changes with the angle of light and view, which fixed maps cannot reproduce. Dendrites are a stylized stripe-and-herringbone pattern. White rust is a flat dielectric overlay. Occlusion is a blurred-height estimate, not ray traced.
