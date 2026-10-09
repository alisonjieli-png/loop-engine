# Corroded metal: rust and verdigris

Rusting steel, heavy flaking rust, copper with verdigris, or polished steel with early rust spots. A warped fractal mask decides where the oxide grows; how far a pixel lies inside a patch picks the layer, from a thin rim through the middle oxide to a thick crust that can flake and pit.

Drip stains run down from each patch: every column is swept downward with an exponential trail whose length follows `streaks`, twice around so the trail wraps across the tile edge. Bare metal keeps a rolled grain and fine scratches and is the only part with metallic set to 1; oxide is a rough dielectric.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `metal_corrosion_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.95 |
| `normal` | `metal_corrosion_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `metal_corrosion_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 1 |
| `metallic` | `metal_corrosion_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `metal_corrosion_height.png` | 1 | linear | white is high |
| `ao` | `metal_corrosion_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Steel plate with orange-brown rust patches and light drip stains.
- `heavy_rust`: Steel almost covered in thick flaking rust with deep pits.
- `verdigris`: Copper with blue-green patina and brown oxide rims.
- `light_bloom`: Mostly bare polished steel with small early rust spots.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `coverage` | float | 0.45 | 0 to 1 | Share of the surface under oxide. |
| `patch_scale` | int | 3 | 1 to 12 | Noise cells across the tile for the corrosion patches: higher values give smaller patches. |
| `pitting` | float | 0.5 | 0 to 1 | Density and depth of pits in the oxide. |
| `streaks` | float | 0.5 | 0 to 1 | Strength of the oxide stains running down from each patch. |
| `flaking` | float | 0.4 | 0 to 1 | Raised, cracked crust in the thick middle of the patches. |
| `metal_roughness` | float | 0.35 | 0.05 to 0.8 | Roughness of the bare metal. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`metal_corrosion.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python metal_corrosion.py --size 1024 --seed 7 --preset heavy_rust --out textures/metal_corrosion
python metal_corrosion.py --width 512 --height 256 --set coverage=1 --orm --out maps
```

`--orm` also writes `metal_corrosion_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import metal_corrosion

maps = metal_corrosion.generate(512, 512, seed=3, preset="heavy_rust")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 36.5 s (24 s to compute, 12.5 s to write the PNG files) with a peak of about 958 MB; 256 x 256 takes about 2.55 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/metal_corrosion/` of your project (for example `python metal_corrosion.py --size 1024 --out path/to/project/baltor/textures/metal_corrosion`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and a height map for parallax (`heightmap_scale` 1). Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.01, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Corrosion is a noise-driven pattern, not an electrochemical simulation; it ignores edges, welds and drainage of a real object. Drip stains always run toward the bottom of the tile. Metal colours are artistic approximations of reflectance. Occlusion is a blurred-height estimate.
