# Water caustics traced onto a pool floor

A swimming pool with a sharp bright web over glazed tiles, tropical shallows over rippled sand, softer caustics over dark rock in deeper water, or high-contrast light on a plain grey card for use as a projected light. The water surface is a periodic height field: fractal gradient noise on lattices of n and n + 1 cells with a steep spectrum, so the main waves rather than fine ripples set the size of the web.

Light falls straight down and every ray is offset against the surface slope by an amount set by `focus` (water depth times refraction strength). Four rays per output pixel are traced to the floor and each adds its energy to the four floor pixels around its landing point, with wrap-around, so the brightness is the ray density: crests focus light into lines and knots, troughs spread it thin. The emissive map holds that light; albedo, height and roughness describe the floor under it.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `water_caustics_albedo.png` | 3 | sRGB | glTF base colour, values 0.03 to 0.92 |
| `normal` | `water_caustics_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `water_caustics_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 1 |
| `height` | `water_caustics_height.png` | 1 | linear | white is high |
| `ao` | `water_caustics_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `water_caustics_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Swimming pool: sharp bright web over pale blue glazed tiles.
- `sandy_shallows`: Tropical shallows: turquoise light over rippled sand, finer web.
- `deep_reef`: Deeper water: soft, dim blue caustics over dark rock.
- `light_cookie`: High-contrast caustic light on a plain grey card, for projecting as light.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `wave_cells` | int | 3 | 1 to 8 | Main wave features across the tile; more cells give a finer caustic web. |
| `focus` | float | 0.55 | 0.05 to 1 | Water depth times refraction strength: low gives soft blotches, high sharp folded lines. |
| `ripples` | float | 0.3 | 0 to 1 | Fine ripples on the surface that break the web into smaller cells. |
| `light` | float | 0.8 | 0.1 to 1 | Brightness of the focused light in the emissive map. |
| `floor` | int | 0 | 0 to 3 | Floor under the water: 0 pool tiles, 1 rippled sand, 2 rough rock, 3 plain grey card. |
| `tiles_across` | int | 8 | 2 to 24 | Pool tiles across the tile (floor 0). |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the light in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`water_caustics.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python water_caustics.py --size 1024 --seed 7 --preset sandy_shallows --out textures/water_caustics
python water_caustics.py --width 512 --height 256 --set wave_cells=8 --orm --out maps
```

`--orm` also writes `water_caustics_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import water_caustics

maps = water_caustics.generate(512, 512, seed=3, preset="sandy_shallows")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 25.2 s (14.2 s to compute, 10.9 s to write the PNG files) with a peak of about 771 MB; 256 x 256 takes about 1.84 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/water_caustics/` of your project (for example `python water_caustics.py --size 1024 --out path/to/project/baltor/textures/water_caustics`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.006, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

As a light cookie, use the `light_cookie` preset's emissive map as the texture of a projector or spot light pointing down; in Godot, a `Decal` with the emissive map as its emission texture also works.

## Limits

One still frame, not an animation. Refraction uses the paraxial approximation (ray offset proportional to the surface slope), light falls straight down and there is no dispersion, absorption or depth-dependent blur, so it is an approximation of real caustics rather than a light transport simulation. Brightness comes from four rays per output pixel and a light smoothing filter, so the finest lines are about a pixel wide at any size. The floor types are simple; the emissive map holds colour only, so the engine sets the emission strength.
