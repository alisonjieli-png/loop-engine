# Fur pelt from strands along a flow field

Brown tabby fur, a short golden pelt with dark rosettes, short glossy black fur, long white fluffy fur in soft locks, or a white coat with round black spots. The flow field, the coat pattern and the strand painting all wrap around the tile edges, so the pelt tiles in both directions.

Every strand starts at a root, follows the flow for three steps and tapers to its tip; `length`, `thickness` and `coverage` set its size and how densely strands cover the undercoat. `swirl` turns the flow away from the main lie, `clumping` pulls tips into locks, `pattern` colours strands by the coat pattern at their roots, `banding` darkens roots and adds a light band near the tips, and `gloss` lowers the roughness along the strand middles.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `fur_strands_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `fur_strands_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `fur_strands_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.3 to 1 |
| `height` | `fur_strands_height.png` | 1 | linear | white is high |
| `ao` | `fur_strands_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Brown tabby cat fur with dark stripes and banded hairs.
- `leopard_rosettes`: Short golden pelt with dark rosettes.
- `black_glossy`: Short glossy black fur lying flat.
- `white_fluffy`: Long white fluffy fur parted into soft locks.
- `dalmatian_spots`: Short white coat with round black spots.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `length` | float | 0.05 | 0.015 to 0.12 | Strand length in texture units. |
| `thickness` | float | 0.0022 | 0.001 to 0.006 | Strand radius at the root in texture units (drawn at least about a pixel wide). |
| `coverage` | float | 3 | 1.5 to 5 | How many strands cover each point on average; low values show the undercoat. |
| `swirl` | float | 0.35 | 0 to 1 | How far the flow turns away from the main lie direction. |
| `clumping` | float | 0.4 | 0 to 1 | How strongly strand tips gather into locks. |
| `pattern` | int | 1 | 0 to 3 | Coat pattern: 0 solid, 1 tabby stripes, 2 spots, 3 rosettes (dark rings). |
| `banding` | float | 0.5 | 0 to 1 | Colour change along each strand: darker root and a light band near the tip. |
| `gloss` | float | 0.3 | 0 to 1 | Sheen of the strands. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`fur_strands.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python fur_strands.py --size 1024 --seed 7 --preset leopard_rosettes --out textures/fur_strands
python fur_strands.py --width 512 --height 256 --set length=0.12 --orm --out maps
```

`--orm` also writes `fur_strands_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import fur_strands

maps = fur_strands.generate(512, 512, seed=3, preset="leopard_rosettes")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 32.3 s (21.1 s to compute, 11.2 s to write the PNG files) with a peak of about 512 MB; 256 x 256 takes about 3.52 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/fur_strands/` of your project (for example `python fur_strands.py --size 1024 --out path/to/project/baltor/textures/fur_strands`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

## Limits

Fur is painted as flat strands in a height field, so it reads as fur lying flat seen from above; it is not hair geometry, cards or shells, and it has no silhouette fuzz, anisotropic hair shading or translucency. Strands are three straight segments each, so long fur looks combed rather than tangled. Coat patterns are stylized periodic fields (stripes, spots, rings), not species markings. Strands are drawn at least about a pixel wide, so the strand count drops at small sizes. Occlusion is a blurred-height estimate.
