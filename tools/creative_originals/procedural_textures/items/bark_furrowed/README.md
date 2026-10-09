# Furrowed tree bark

Oak-like plates, pine plates, ash ridges, stringy cedar or old mossy bark. Plates are tall Voronoi cells warped so the furrows wander; interlaced ridges come from ridged noise stretched along the trunk, which splits and rejoins in a diamond net; stringy bark is a field of thin fibre strips.

Fibres stretched along the trunk texture every surface. Plates can flake in steps parallel to their edges and break along horizontal cross-checks. Lichen settles on the plates and moss fills the furrows.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `bark_furrowed_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.8 |
| `normal` | `bark_furrowed_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `bark_furrowed_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.55 to 1 |
| `height` | `bark_furrowed_height.png` | 1 | linear | white is high |
| `ao` | `bark_furrowed_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey-brown oak-like plates with deep furrows and some lichen.
- `pine_plates`: Reddish pine plates with dark furrows and flaky checks.
- `ash_ridges`: Grey interlaced ridges in a diamond net.
- `cedar_stringy`: Red-brown stringy fibres in long strips.
- `mossy_old`: Old dark bark with moss filling the furrows.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `pattern` | int | 0 | 0 to 2 | Bark structure: 0 plates, 1 interlaced ridges, 2 stringy fibres. |
| `ridges_across` | int | 6 | 2 to 16 | Plates or ridges across the tile width. |
| `plate_length` | int | 1 | 1 to 6 | Plate rows down the tile (fewer rows give longer plates). |
| `furrow_depth` | float | 0.7 | 0.1 to 1 | Depth of the furrows between plates or ridges. |
| `furrow_width` | float | 0.12 | 0.02 to 0.4 | Width of the furrows, in plate widths. |
| `cross_checks` | float | 0.5 | 0 to 1 | Horizontal cracks breaking the plates. |
| `flakes` | float | 0.4 | 0 to 1 | Layered flaking inside the plates: stepped rims parallel to the plate edge. |
| `lichen` | float | 0.2 | 0 to 1 | Pale lichen patches on the plates. |
| `moss` | float | 0 | 0 to 1 | Moss in the furrows. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`bark_furrowed.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python bark_furrowed.py --size 1024 --seed 7 --preset pine_plates --out textures/bark_furrowed
python bark_furrowed.py --width 512 --height 256 --set pattern=2 --orm --out maps
```

`--orm` also writes `bark_furrowed_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import bark_furrowed

maps = bark_furrowed.generate(512, 512, seed=3, preset="pine_plates")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 22.7 s (15.4 s to compute, 7.3 s to write the PNG files) with a peak of about 898 MB; 256 x 256 takes about 1.27 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/bark_furrowed/` of your project (for example `python bark_furrowed.py --size 1024 --out path/to/project/baltor/textures/bark_furrowed`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and a height map for parallax (`heightmap_scale` 3). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.04, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Three stylized bark structures from noise and Voronoi cells; species are suggested by colour and proportion, not reproduced. The texture assumes a cylinder unwrapped along its axis, so it does not taper or bend around branches. Occlusion is a blurred-height estimate.
