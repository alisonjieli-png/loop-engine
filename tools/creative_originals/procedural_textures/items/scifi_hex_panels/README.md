# Science fiction hexagonal hull panels

A light grey hull with cyan lights, a dark reactor with orange glowing seams, clean white lab panels or bolted olive armour. Panels are the cells of a hexagonal lattice with an even row count, so the lattice repeats on a square tile. The distance to the cell border gives a bevelled rim and an inset centre plate.

A hash of each panel picks its type: plain, vented with parallel slots, a glowing inset light or bolted with six bolts inside the corners. Seams can glow (`seam_glow`), which the emissive map carries alone, and `wear` scuffs paint off the rims to bare metal.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `scifi_hex_panels_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.92 |
| `normal` | `scifi_hex_panels_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `scifi_hex_panels_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `metallic` | `scifi_hex_panels_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `scifi_hex_panels_height.png` | 1 | linear | white is high |
| `ao` | `scifi_hex_panels_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `scifi_hex_panels_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Light grey hull with cyan panel lights.
- `dark_reactor`: Dark panels with orange glowing seams.
- `white_lab`: Clean white panels with fine seams and few details.
- `military_olive`: Olive drab armour hexes, bolted and scuffed.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `hexes_across` | int | 7 | 3 to 26 | Hexagons across the tile (7, 12, 14, 19 or 26 keep them closest to regular). |
| `seam_width` | float | 0.05 | 0.01 to 0.2 | Gap between panels, in hexagon widths. |
| `bevel` | float | 0.08 | 0.01 to 0.25 | Width of the bevelled rim, in hexagon widths. |
| `light_share` | float | 0.15 | 0 to 1 | Share of panels with a glowing inset. |
| `vent_share` | float | 0.2 | 0 to 1 | Share of panels with vent slots. |
| `seam_glow` | float | 0 | 0 to 1 | Glow inside the seams. |
| `wear` | float | 0.25 | 0 to 1 | Scuffed paint on the rims, showing metal. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and glow in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`scifi_hex_panels.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python scifi_hex_panels.py --size 1024 --seed 7 --preset dark_reactor --out textures/scifi_hex_panels
python scifi_hex_panels.py --width 512 --height 256 --set hexes_across=26 --orm --out maps
```

`--orm` also writes `scifi_hex_panels_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import scifi_hex_panels

maps = scifi_hex_panels.generate(512, 512, seed=3, preset="dark_reactor")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 29.6 s (17.2 s to compute, 12.4 s to write the PNG files) with a peak of about 843 MB; 256 x 256 takes about 1.88 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/scifi_hex_panels/` of your project (for example `python scifi_hex_panels.py --size 1024 --out path/to/project/baltor/textures/scifi_hex_panels`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.01, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

## Limits

The hexagonal lattice is squashed slightly to repeat on a square tile: about 1 percent for 7, 12, 14, 19 or 26 hexagons across, up to 15 percent for 3, 4 or 6. Panel types are chosen at random, with no hierarchy of large and small panels. Lights and glowing seams are emissive colour, not light sources. Occlusion is a blurred-height estimate, not ray traced.
