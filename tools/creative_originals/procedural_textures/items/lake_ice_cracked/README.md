# Cracked lake ice with bubbles and skate scratches

Black ice with white fracture planes and scattered bubbles, clear ice full of stacked methane bubbles, milky rink ice criss-crossed by skate scratches, or blue ice broken into plates by a dense crack network. Long fractures are jagged polylines that wander across the tile and wrap around its edges; each has a bright core line and a fainter sheet offset to one side, which reads as a crack plane slanting down into clear ice. Short twigs branch from them, and a Worley diagram broken up by noise adds the thinner network between plates.

Bubbles are small white rings; methane bubbles are stacks of soft white discs with small offsets. Cracks and bubbles live inside the ice, so they change only the colour, while skate scratches and a faint undulation are surface features that also shape height, normals and roughness. `milkiness` blends clear black ice toward white snow ice by a fractal noise field.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `lake_ice_cracked_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `lake_ice_cracked_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `lake_ice_cracked_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.03 to 0.8 |
| `height` | `lake_ice_cracked_height.png` | 1 | linear | white is high |
| `ao` | `lake_ice_cracked_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Black ice: clear dark ice with white fracture planes and scattered bubbles.
- `methane_bubbles`: Clear ice full of stacked white methane bubbles, few cracks.
- `skating_rink`: Milky outdoor rink ice criss-crossed by skate scratches.
- `pressure_cracked`: Blue ice broken into plates by a dense crack network and fractures.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `fractures` | int | 6 | 0 to 20 | Long fracture lines wandering across the tile. |
| `network` | float | 0.3 | 0 to 1 | Polygonal network of thin cracks between ice plates. |
| `plates` | int | 5 | 2 to 16 | Plates across the tile for the crack network. |
| `bubbles` | float | 0.45 | 0 to 1 | Scattered small air bubbles. |
| `pancakes` | float | 0.15 | 0 to 1 | Stacks of flat white methane bubbles. |
| `scratches` | float | 0.2 | 0 to 1 | Skate scratches cut into the surface. |
| `milkiness` | float | 0.15 | 0 to 1 | Share of white, cloudy snow ice against clear black ice. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`lake_ice_cracked.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python lake_ice_cracked.py --size 1024 --seed 7 --preset methane_bubbles --out textures/lake_ice_cracked
python lake_ice_cracked.py --width 512 --height 256 --set fractures=20 --orm --out maps
```

`--orm` also writes `lake_ice_cracked_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import lake_ice_cracked

maps = lake_ice_cracked.generate(512, 512, seed=3, preset="methane_bubbles")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 22.2 s (13.5 s to compute, 8.7 s to write the PNG files) with a peak of about 772 MB; 256 x 256 takes about 1.52 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/lake_ice_cracked/` of your project (for example `python lake_ice_cracked.py --size 1024 --out path/to/project/baltor/textures/lake_ice_cracked`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Cracks and bubbles inside the ice are painted into the albedo, not modelled in depth, so there is no parallax or refraction through clear ice; a shader that wants depth can use the albedo as a view-independent layer under a glossy surface. Fracture planes are a bright line with a fainter offset sheet, a stylized reading of slanted cracks. The crack network is a Worley diagram broken by noise. Bubbles smaller than about half a pixel at the output size are left out. Occlusion is a blurred-height estimate.
