# Honeycomb with capped and honey-filled cells

Golden comb with patches of capped cells among cells of honey, new white comb that is mostly empty, dark old brood comb with brown caps, or large cells brimming with amber honey. The cells are the Voronoi regions of a hexagonal lattice with an even row count, so the comb tiles in both directions.

`wall` sets the wax wall thickness and `irregularity` how unevenly the bees built the cells. `capped` seals a share of the cells with domed wax caps, gathered in patches by smooth noise; of the open cells, `honey` fills a share with glossy honey and leaves the rest empty. `age` darkens the wax and the caps from new white comb to old brood comb.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `honeycomb_comb_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `honeycomb_comb_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `honeycomb_comb_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 1 |
| `height` | `honeycomb_comb_height.png` | 1 | linear | white is high |
| `ao` | `honeycomb_comb_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Golden comb with patches of capped cells among cells full of honey.
- `fresh_white`: New white comb, mostly empty, with thin clean walls.
- `brood_comb`: Dark old brood comb with brown domed caps.
- `brimming_honey`: Large open cells brimming with amber honey.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `cells` | int | 9 | 4 to 26 | Cells across the tile; the row count is the even number that keeps the hexagons near regular. |
| `wall` | float | 0.1 | 0.04 to 0.22 | Wax wall thickness as a share of the cell width. |
| `capped` | float | 0.5 | 0 to 1 | Share of cells sealed with a wax cap. |
| `honey` | float | 0.75 | 0 to 1 | Share of open cells holding honey; the rest are empty. |
| `irregularity` | float | 0.3 | 0 to 1 | How unevenly the cells are built: jitter of the cell centres. |
| `age` | float | 0.15 | 0 to 1 | Darkening of the wax with use: 0 new white comb, 1 old dark brood comb. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`honeycomb_comb.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python honeycomb_comb.py --size 1024 --seed 7 --preset fresh_white --out textures/honeycomb_comb
python honeycomb_comb.py --width 512 --height 256 --set cells=26 --orm --out maps
```

`--orm` also writes `honeycomb_comb_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import honeycomb_comb

maps = honeycomb_comb.generate(512, 512, seed=3, preset="fresh_white")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 28 s (13.1 s to compute, 14.9 s to write the PNG files) with a peak of about 645 MB; 256 x 256 takes about 1.4 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/honeycomb_comb/` of your project (for example `python honeycomb_comb.py --size 1024 --out path/to/project/baltor/textures/honeycomb_comb`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 1.5). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.02, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Cells are seen face-on as a height field: the depth of an empty cell is a short drop to a dark floor, not a modelled tube, and honey is an opaque glossy surface with no translucency or refraction. Larvae, pollen, bees and broken comb are out of scope. Capped and open cells gather by smooth noise rather than by colony behaviour. The hexagons come from a lattice made near-regular for the tile, so very low cell counts squash them slightly. Occlusion is a blurred-height estimate.
