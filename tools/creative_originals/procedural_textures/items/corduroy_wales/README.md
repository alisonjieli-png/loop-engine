# Corduroy wales from pinwale to wide wale

Camel medium wale, navy pinwale, rust wide wale with crushed cords, olive thick-and-thin or lustrous burgundy needlecord. A whole number of wales runs down the tile, so the cloth repeats; every other wale can be wider when `alternate` is above zero.

Each wale is a rounded cord of cut pile with a grain of fibre tips; `groove` sets how much of the ground weave shows between cords. `pile` strengthens the grain and its lean streaks, `sheen` adds lustre to the cord tops and lowers their roughness, and `wear` flattens and lightens the tops in patches.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `corduroy_wales_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `corduroy_wales_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `corduroy_wales_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.35 to 1 |
| `height` | `corduroy_wales_height.png` | 1 | linear | white is high |
| `ao` | `corduroy_wales_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Camel medium-wale corduroy.
- `pinwale_navy`: Navy pinwale (needlecord) with fine, shallow grooves.
- `wide_wale_rust`: Rust wide-wale corduroy with worn, crushed cords.
- `thick_thin_olive`: Olive thick-and-thin corduroy: wide and narrow wales alternate.
- `lustre_burgundy`: Burgundy lustrous needlecord with a velvet sheen.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `wales` | int | 14 | 4 to 48 | Wales across the tile width: about 40 is pinwale or needlecord, 6 is wide wale; rounded up to an even count when wales alternate. |
| `groove` | float | 0.18 | 0.05 to 0.4 | Width of the groove between wales as a share of the wale spacing. |
| `pile` | float | 0.6 | 0 to 1 | Strength of the cut-pile grain on the cords. |
| `sheen` | float | 0.3 | 0 to 1 | Lustre of the pile on the cord tops. |
| `wear` | float | 0.15 | 0 to 1 | Crushed, lighter cord tops in patches. |
| `alternate` | float | 0 | 0 to 0.7 | Thick-and-thin corduroy: how much wider every other wale is than its neighbour. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`corduroy_wales.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python corduroy_wales.py --size 1024 --seed 7 --preset pinwale_navy --out textures/corduroy_wales
python corduroy_wales.py --width 512 --height 256 --set wales=48 --orm --out maps
```

`--orm` also writes `corduroy_wales_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import corduroy_wales

maps = corduroy_wales.generate(512, 512, seed=3, preset="pinwale_navy")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 23.3 s (8.3 s to compute, 15 s to write the PNG files) with a peak of about 559 MB; 256 x 256 takes about 1.24 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/corduroy_wales/` of your project (for example `python corduroy_wales.py --size 1024 --out path/to/project/baltor/textures/corduroy_wales`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Wales are rounded height profiles with fibre noise, not modelled tufts; the pile lean shows as tone and roughness, so the directional sheen of real corduroy (which changes with view angle) is only approximated. Wales run along V only; rotate the UVs for horizontal cords. Wear is noise-driven, not placed at knees or elbows. The groove weave fades out where it would be finer than a few pixels. Occlusion is a blurred-height estimate, not ray traced.
