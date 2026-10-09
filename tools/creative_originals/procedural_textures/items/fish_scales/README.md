# Overlapping fish scales with growth rings

Silver baitfish scales with a blue-green and pink sheen, white koi with large red patches, large bronze carp scales with dark net-like edges, or small olive trout scales with dark spots. Scales sit in offset rows with whole counts across and down, so the skin tiles; the row above covers the front of every scale, and only its rear crescent shows.

`columns` sets the scale size and `exposure` how much of each scale shows. `circuli` and `radii` cut growth rings and radial grooves, `edge_pigment` darkens the free edges, `iridescence` turns the colour across each scale, and `pattern` adds koi patches or trout spots, coloured scale by scale. Silver presets carry a metallic map, so the scales reflect like metal while the skin between them stays dielectric.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `fish_scales_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `fish_scales_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `fish_scales_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.12 to 1 |
| `metallic` | `fish_scales_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `fish_scales_height.png` | 1 | linear | white is high |
| `ao` | `fish_scales_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Silver baitfish scales with a blue-green and pink sheen.
- `koi_kohaku`: White koi scales with large red patches and a faint net.
- `carp_bronze`: Large bronze carp scales with dark pigmented edges.
- `trout_spotted`: Small olive trout scales with dark spots and a pink sheen.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `columns` | int | 12 | 4 to 32 | Scales across the tile; the row count follows from the exposure. |
| `exposure` | float | 0.42 | 0.25 to 0.7 | Row spacing as a share of the scale diameter: how much of each scale shows. |
| `circuli` | float | 0.5 | 0 to 1 | Depth of the growth rings around each scale's centre. |
| `radii` | float | 0.3 | 0 to 1 | Depth of the grooves radiating from the growth centre. |
| `edge_pigment` | float | 0.35 | 0 to 1 | Dark pigment along the free edge of each scale (a net pattern). |
| `iridescence` | float | 0.35 | 0 to 1 | Colour sheen turning across each scale. |
| `pattern` | int | 0 | 0 to 2 | 0 even colour, 1 large patches of a second colour (koi), 2 dark spots (trout). |
| `gloss` | float | 0.7 | 0 to 1 | Wet gloss of the skin. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`fish_scales.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python fish_scales.py --size 1024 --seed 7 --preset koi_kohaku --out textures/fish_scales
python fish_scales.py --width 512 --height 256 --set columns=32 --orm --out maps
```

`--orm` also writes `fish_scales_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import fish_scales

maps = fish_scales.generate(512, 512, seed=3, preset="koi_kohaku")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 20.9 s (11.1 s to compute, 9.8 s to write the PNG files) with a peak of about 561 MB; 256 x 256 takes about 1.19 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/fish_scales/` of your project (for example `python fish_scales.py --size 1024 --out path/to/project/baltor/textures/fish_scales`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Scales are round discs of one size in regular offset rows; the lateral line, fins, the change of scale size along the body and ctenoid spines are out of scope. The head is toward the top of the tile. The sheen is a hue turning across each scale, a stylized stand-in for thin-film reflection that does not change with view angle. Patches and spots are noise fields sampled once per scale. Growth rings fade out where they would be finer than a couple of pixels. Occlusion is a blurred-height estimate.
