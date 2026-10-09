# Diamond tread plate

Aluminium, dirty dark steel, yellow painted or fine-pitched bright tread plate. The tile is a grid of cells; each cell holds one elongated lug, a capsule turned to +45 or -45 degrees in a checkerboard, which gives the familiar herringbone of tread plate and repeats with the grid.

Lugs have a rounded dome profile. Foot traffic polishes the lug tops (`wear`), dirt collects in the valleys (`dirt`), and on painted plate (`paint`) the coating wears through to bare metal on the lugs first. The metallic map follows the bare metal.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `diamond_plate_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `diamond_plate_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `diamond_plate_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.08 to 1 |
| `metallic` | `diamond_plate_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `diamond_plate_height.png` | 1 | linear | white is high |
| `ao` | `diamond_plate_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Aluminium tread plate, lightly worn.
- `steel_dirty`: Dark steel tread plate with dirt in the valleys.
- `painted_yellow`: Yellow painted tread plate worn to metal on the lug tops.
- `fine_pattern`: Fine-pitched bright plate with short lugs.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `lugs_across` | int | 6 | 2 to 20 | Lug cells across the tile (and down it). |
| `lug_length` | float | 0.7 | 0.3 to 1.1 | Lug length as a share of the cell diagonal. |
| `lug_width` | float | 0.22 | 0.05 to 0.35 | Lug width as a share of the cell. |
| `wear` | float | 0.5 | 0 to 1 | Polish of the lug tops (and paint worn through on painted plate). |
| `dirt` | float | 0.15 | 0 to 1 | Dirt in the valleys. |
| `paint` | float | 0 | 0 to 1 | Paint coverage (0 bare metal, 1 fully painted plate). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`diamond_plate.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python diamond_plate.py --size 1024 --seed 7 --preset steel_dirty --out textures/diamond_plate
python diamond_plate.py --width 512 --height 256 --set lugs_across=20 --orm --out maps
```

`--orm` also writes `diamond_plate_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import diamond_plate

maps = diamond_plate.generate(512, 512, seed=3, preset="steel_dirty")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 20.5 s (8.8 s to compute, 11.7 s to write the PNG files) with a peak of about 640 MB; 256 x 256 takes about 1.3 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/diamond_plate/` of your project (for example `python diamond_plate.py --size 1024 --out path/to/project/baltor/textures/diamond_plate`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and a height map for parallax (`heightmap_scale` 1). Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Lugs are identical capsules on a regular grid; real plates differ in lug shape by standard and maker. Wear follows lug height and noise, not walking paths. The lug relief is large for a normal map alone, so parallax or displacement helps at close range. Occlusion is a blurred-height estimate, not ray traced.
