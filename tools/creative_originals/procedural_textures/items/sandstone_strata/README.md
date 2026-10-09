# Layered sandstone

Desert red and cream bands, pale buff building stone, coastal honeycomb rock, swirled dune sandstone or thin grey beds. Strata of uneven thickness run across the tile, and low-frequency noise waves their boundaries.

Each stratum takes a colour and a hardness; soft strata are eroded back so hard ones stand proud. Inside the strata, cross-bedding laminae run at an incline that alternates between strata, using whole numbers of cycles so the texture repeats. `honeycomb` sinks rounded weathering pits.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `sandstone_strata_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.88 |
| `normal` | `sandstone_strata_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `sandstone_strata_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.6 to 1 |
| `height` | `sandstone_strata_height.png` | 1 | linear | white is high |
| `ao` | `sandstone_strata_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Desert red and cream banded sandstone.
- `buff`: Pale buff building sandstone with faint bedding.
- `tafoni_coast`: Coastal sandstone with honeycomb weathering.
- `swirled`: Strongly cross-bedded orange and white dune sandstone.
- `grey_flagstone`: Grey-green layered sandstone with thin beds.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `strata` | int | 9 | 2 to 30 | Strata across the tile height. |
| `thickness_variation` | float | 0.6 | 0 to 1 | How unequal the strata are in thickness. |
| `waviness` | float | 0.4 | 0 to 1 | How much the strata boundaries wave. |
| `cross_bedding` | float | 0.5 | 0 to 1 | Visibility of the inclined laminae inside the strata. |
| `erosion` | float | 0.5 | 0 to 1 | How far soft strata are worn back behind hard ones. |
| `honeycomb` | float | 0 | 0 to 1 | Honeycomb weathering pits (tafoni). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`sandstone_strata.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python sandstone_strata.py --size 1024 --seed 7 --preset buff --out textures/sandstone_strata
python sandstone_strata.py --width 512 --height 256 --set strata=30 --orm --out maps
```

`--orm` also writes `sandstone_strata_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import sandstone_strata

maps = sandstone_strata.generate(512, 512, seed=3, preset="buff")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 18.1 s (9.1 s to compute, 9 s to write the PNG files) with a peak of about 609 MB; 256 x 256 takes about 1.25 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/sandstone_strata/` of your project (for example `python sandstone_strata.py --size 1024 --out path/to/project/baltor/textures/sandstone_strata`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 2). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.03, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Strata run across the tile height, so a wall must be oriented with its bedding horizontal in UV space. Cross-bedding is a periodic lamina pattern, not a sediment simulation. Honeycomb pits are Voronoi cells. Occlusion is a blurred-height estimate.
