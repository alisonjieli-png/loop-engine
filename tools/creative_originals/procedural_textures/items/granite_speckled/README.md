# Speckled granite

Grey, rose, black, flamed grey or blue-grey crystalline stone. Grains are cells of a fine Voronoi diagram on the torus; a hash of each cell picks its mineral from the preset's mix, and a soft gradient toward the cell centre suggests cleavage faces.

Large blocky feldspar crystals float in the groundmass when `phenocrysts` is above zero. `finish` runs from polished (flat and glossy, hairline grain boundaries) to flamed (rough and matte, quartz standing proud).

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `granite_speckled_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `granite_speckled_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `granite_speckled_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `height` | `granite_speckled_height.png` | 1 | linear | white is high |
| `ao` | `granite_speckled_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Polished grey granite: white feldspar, grey quartz, black mica.
- `rose`: Polished pink granite with salmon feldspar and large crystals.
- `black_galaxy`: Polished black stone with sparse bronze flecks.
- `flamed_grey`: Flamed grey granite: rough, matte, quartz raised.
- `blue_larvikite`: Blue-grey stone with large feldspar crystals and a soft sheen.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `grains_across` | int | 40 | 12 to 128 | Mineral grains across the tile (higher is finer). |
| `feldspar` | float | 0.55 | 0 to 1 | Share of feldspar grains (the main colour). |
| `dark_minerals` | float | 0.15 | 0 to 0.6 | Share of dark mica and hornblende grains; the rest is quartz. |
| `phenocrysts` | float | 0.2 | 0 to 1 | Amount of large blocky feldspar crystals. |
| `finish` | float | 0.1 | 0 to 1 | Surface finish from polished (0) through honed to flamed (1). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`granite_speckled.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python granite_speckled.py --size 1024 --seed 7 --preset rose --out textures/granite_speckled
python granite_speckled.py --width 512 --height 256 --set grains_across=128 --orm --out maps
```

`--orm` also writes `granite_speckled_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import granite_speckled

maps = granite_speckled.generate(512, 512, seed=3, preset="rose")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 29.4 s (14.3 s to compute, 15.1 s to write the PNG files) with a peak of about 658 MB; 256 x 256 takes about 1.84 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/granite_speckled/` of your project (for example `python granite_speckled.py --size 1024 --out path/to/project/baltor/textures/granite_speckled`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.8) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Grains are Voronoi cells with one colour each, an approximation of crystal fabric; there is no twinning beyond a single line, no reflective flake and no real mineral optics. Colours are artistic, not matched to named quarries. Occlusion is a blurred-height estimate.
