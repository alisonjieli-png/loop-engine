# Cloud layer: cumulus, stratus, cirrus and mackerel sky

Fair-weather cumulus with grey shaded sides, an overcast stratus sheet with thin patches, high cirrus streaks and hooks, a mackerel sky of small puffs in rows, or a dense dark storm. Each kind is its own density field: cumulus is fractal noise cut at the coverage quantile and eroded by inverted Worley noise into cauliflower edges; stratus is broad noise stretched along the width; cirrus is stretched noise sheared by a slow warp and thinned by a ridged field; the mackerel sky multiplies cellular puffs by a wave that sets them in rows.

Light comes from `sun_angle` at a fixed elevation: the slope of the density toward the sun brightens sunward edges and shades the far side, a short sample of cloud toward the sun adds soft shadow, and thick cores darken by `shading`. The albedo carries the lit colour and its alpha the density with soft edges, for blending over a sky; height and normals follow the density.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `cloud_layer_albedo.png` | 4 | sRGB | glTF base colour, values 0.15 to 1 |
| `normal` | `cloud_layer_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `cloud_layer_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.6 to 1 |
| `height` | `cloud_layer_height.png` | 1 | linear | white is high |
| `ao` | `cloud_layer_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Fair-weather cumulus: separate white heaps with grey shaded sides.
- `overcast_stratus`: Overcast stratus: a nearly closed grey sheet with soft thin patches.
- `cirrus_wisps`: High cirrus: thin bright streaks and hooks across a clear sky.
- `mackerel_sky`: Mackerel sky: rows of small rounded altocumulus puffs.
- `storm_nimbus`: Storm: dense dark towering cloud with bright rims, little clear sky.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `kind` | int | 0 | 0 to 3 | 0 cumulus, 1 stratus, 2 cirrus, 3 mackerel (altocumulus in rows). |
| `coverage` | float | 0.45 | 0.05 to 1 | Share of the sky covered by cloud. |
| `cells` | int | 3 | 1 to 10 | Cloud features across the tile. |
| `billow` | float | 0.6 | 0 to 1 | Cauliflower erosion of the cloud edges (cumulus and mackerel). |
| `softness` | float | 0.4 | 0.05 to 1 | Width of the soft edge between cloud and clear sky. |
| `sun_angle` | float | 0.375 | 0 to 1 | Direction the sunlight comes from across the layer, in turns from +U. |
| `shading` | float | 0.6 | 0 to 1 | Self-shadowing: how dark the far sides and thick cores become. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`cloud_layer.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python cloud_layer.py --size 1024 --seed 7 --preset overcast_stratus --out textures/cloud_layer
python cloud_layer.py --width 512 --height 256 --set kind=3 --orm --out maps
```

`--orm` also writes `cloud_layer_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import cloud_layer

maps = cloud_layer.generate(512, 512, seed=3, preset="overcast_stratus")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 17 s (8.3 s to compute, 8.7 s to write the PNG files) with a peak of about 452 MB; 256 x 256 takes about 1.06 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/cloud_layer/` of your project (for example `python cloud_layer.py --size 1024 --out path/to/project/baltor/textures/cloud_layer`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses alpha blending, so the material sorts with other transparent surfaces.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.5) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `transparent: true`.

For a sky dome, map the tile on a large plane high above the scene or on the inside of a dome with a planar projection, and blend it over the sky gradient; scrolling the UVs slowly animates drift.

## Limits

A flat layer, not volumetric: lighting is a slope term toward the sun with a short sample of cloud in that direction and a darkening of thick cores, so it is an approximation of scattering that suits a sky seen from below or at a distance. The texture tiles, so a wide sky shows the repeat unless two scales are blended. Clouds do not move or change; the albedo alpha suits blending over a sky colour or gradient, and engines sort alpha-blended layers with other transparent surfaces. Height and normals describe density, not real cloud geometry.
