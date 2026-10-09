# Starfield with nebula gas and dust lanes

A deep field of faint stars over violet gas, a red and teal emission nebula torn by dust lanes, a dense star cluster with diffraction spikes, or a nearly empty field of cool stars. Stars are drawn in texture space from a seeded sequence, so a seed keeps its sky at every output size. Brightness follows a power law, and each star's colour comes from a blackbody temperature: Planck's law is integrated over the visible band against a multi-lobe Gaussian fit of the CIE 1931 colour-matching functions and converted to linear sRGB.

Gas is domain-warped fractal noise through two colour ramps per preset; ridged noise carves dust lanes that dim both the gas and the stars behind them. Light is added in linear units and encoded as sRGB at the end, so halos fall off smoothly. The emissive map is the light; the albedo is near black with a faint copy of the glow and the dust tint, so the material still reads under scene lighting.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `starfield_nebula_albedo.png` | 3 | sRGB | glTF base colour, values 0 to 0.85 |
| `normal` | `starfield_nebula_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `starfield_nebula_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.4 to 1 |
| `height` | `starfield_nebula_height.png` | 1 | linear | white is high |
| `ao` | `starfield_nebula_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `starfield_nebula_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Deep field: many faint stars over faint violet and blue gas.
- `emission_nebula`: Bright red and teal gas torn by dark dust lanes, fewer stars.
- `star_cluster`: A dense cluster of hot bright stars with diffraction spikes and little gas.
- `dark_void`: Sparse cool stars and faint brown dust in a nearly empty field.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `star_count` | int | 1600 | 100 to 6000 | Stars drawn in the tile. |
| `bright_stars` | float | 0.35 | 0 to 1 | Share of bright stars: 0 nearly all faint, 1 many bright ones. |
| `star_size` | float | 1 | 0.5 to 3 | Apparent star size; brighter stars are drawn larger. |
| `spikes` | float | 0.3 | 0 to 1 | Four-point diffraction spikes on bright stars, 0 none. |
| `star_temperature` | float | 6500 | 3000 to 15000 | Typical star temperature in kelvin: low gives orange stars, high blue-white ones. |
| `nebula` | float | 0.6 | 0 to 1 | Amount and brightness of glowing gas. |
| `nebula_scale` | int | 2 | 1 to 8 | Cloud features across the tile; larger values give smaller clouds. |
| `swirl` | float | 0.5 | 0 to 1 | Domain warping that pulls the gas into filaments and swirls. |
| `dust` | float | 0.35 | 0 to 1 | Dark dust lanes that dim the gas and the stars behind them. |
| `cluster` | float | 0 | 0 to 1 | Share of stars gathered in a cluster around the middle of the tile. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the light in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`starfield_nebula.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python starfield_nebula.py --size 1024 --seed 7 --preset emission_nebula --out textures/starfield_nebula
python starfield_nebula.py --width 512 --height 256 --set star_count=6000 --orm --out maps
```

`--orm` also writes `starfield_nebula_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import starfield_nebula

maps = starfield_nebula.generate(512, 512, seed=3, preset="emission_nebula")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 36.6 s (15.1 s to compute, 21.5 s to write the PNG files) with a peak of about 868 MB; 256 x 256 takes about 2.25 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/starfield_nebula/` of your project (for example `python starfield_nebula.py --size 1024 --out path/to/project/baltor/textures/starfield_nebula`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.3) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

For a backdrop, put the tile on a large plane or the inside of a dome and let the emission carry it (an unshaded material in Godot shows the emissive map as is). Set `uv1_scale` so a star is no larger than a few screen pixels.

## Limits

A flat tile, not an equirectangular or cube-map sky: wrapped on a sphere it pinches toward the poles, and repeating it shows the same stars again. Star colours come from blackbody temperatures through an approximate colour-matching fit, not from a catalogue; brightness, sizes and spikes are artistic, and stars smaller than a pixel fade out at small output sizes. Gas and dust are noise, not a radiative transfer model. Height and normals are shallow and only follow the gas; occlusion is a stand-in from the dust. The emissive map holds colour only, so the engine sets the emission strength.
