# CRT phosphor mask: aperture grille, delta dots and slots

An aperture grille of continuous red, green and blue stripes crossed by two thin damper wire shadows, a delta shadow mask of round dots in triangles, a slot mask of short staggered slots, or a coarse arcade monitor with deep scanlines showing a picture. The delta lattice offsets odd rows by half a dot and colours dot i of row j by (i + 2 (j mod 2)) mod 3, so every triangle of neighbouring dots holds one dot of each colour.

Each subpixel has a soft Gaussian profile, and the electron beam adds scanlines with a Gaussian brightness profile across each line. The screen shows flat white or, with `picture`, a smooth colourful image sampled per subpixel. The emissive map is the lit screen; the albedo is the unlit phosphor layer, grey spots on a black matrix, with the spots slightly raised.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `crt_phosphor_mask_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.6 |
| `normal` | `crt_phosphor_mask_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `crt_phosphor_mask_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.1 to 0.9 |
| `height` | `crt_phosphor_mask_height.png` | 1 | linear | white is high |
| `ao` | `crt_phosphor_mask_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `crt_phosphor_mask_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Aperture grille: continuous RGB stripes with soft scanlines.
- `shadow_mask_delta`: Delta shadow mask: round RGB dots in triangles, fine pitch.
- `slot_mask`: Slot mask: short staggered RGB slots, as on many consumer sets.
- `arcade_low_res`: Low-resolution arcade monitor: coarse slots, deep scanlines, a picture.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `mask` | int | 0 | 0 to 2 | 0 aperture grille stripes, 1 delta shadow mask dots, 2 slot mask. |
| `triads_across` | int | 16 | 6 to 160 | Red, green and blue triads across the tile. |
| `scanlines` | int | 16 | 4 to 240 | Scanlines down the tile. |
| `scan_strength` | float | 0.5 | 0 to 1 | How dark the gaps between scanlines are. |
| `picture` | float | 0.3 | 0 to 1 | Blend from a flat white screen (0) to a colourful procedural picture (1). |
| `spot` | float | 0.6 | 0.1 to 1 | Size of each phosphor spot within its cell, with soft falloff. |
| `glow` | float | 0.9 | 0.1 to 1 | Brightness of the lit phosphors in the emissive map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the light in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`crt_phosphor_mask.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python crt_phosphor_mask.py --size 1024 --seed 7 --preset shadow_mask_delta --out textures/crt_phosphor_mask
python crt_phosphor_mask.py --width 512 --height 256 --set mask=2 --orm --out maps
```

`--orm` also writes `crt_phosphor_mask_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import crt_phosphor_mask

maps = crt_phosphor_mask.generate(512, 512, seed=3, preset="shadow_mask_delta")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 20.9 s (8.6 s to compute, 12.3 s to write the PNG files) with a peak of about 742 MB; 256 x 256 takes about 1.6 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/crt_phosphor_mask/` of your project (for example `python crt_phosphor_mask.py --size 1024 --out path/to/project/baltor/textures/crt_phosphor_mask`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.5) and the height map through a Displacement node (scale 0.001, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

As an overlay, multiply the emissive map over a rendered game frame at a scale where one triad covers a few screen pixels, or use it directly as the emissive texture of a monitor model.

## Limits

A close-up pattern, not a display simulation: phosphor spots have Gaussian profiles, the beam adds a fixed scanline profile, and there is no convergence error, bloom, persistence, curvature or glass reflection. The picture is a smooth procedural image sampled per subpixel. Counts are whole numbers across the tile so the mask repeats; fine pitches alias when a stripe or dot is narrower than about three pixels. Phosphor primaries are approximate sRGB colours.
