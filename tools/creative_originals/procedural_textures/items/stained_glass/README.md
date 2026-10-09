# Leaded stained glass in three layouts

Cathedral glass in irregular jewel-coloured pieces, leaded diamond quarries of pale tinted glass with a few coloured panes, Victorian ruby circles in amber squares with cobalt accents, or large streaky opalescent amber and green pieces in thin copper foil. Panes come from the cells of a Worley diagram, from a lattice turned 45 degrees, or from circles inscribed in a square grid, and every pane takes its glass colour from the preset's weighted palette by a hash of its index.

Glass carries streaks in a direction chosen per pane, small seed bubbles and a wavering thickness. Lead came is drawn from the exact distance to each pane border with a rounded, raised profile, dull grey and metallic, and the quarries get solder blobs where leads cross. The emissive map is the light through the glass for a backlit window; the albedo is the darker colour glass shows when lit from the front.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `stained_glass_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.9 |
| `normal` | `stained_glass_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `stained_glass_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.05 to 0.9 |
| `metallic` | `stained_glass_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `stained_glass_height.png` | 1 | linear | white is high |
| `ao` | `stained_glass_ao.png` | 1 | linear | white is unoccluded |
| `emissive` | `stained_glass_emissive.png` | 3 | sRGB | glTF emissive colour |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Cathedral glass: irregular jewel-coloured pieces in dark lead.
- `diamond_quarries`: Leaded diamond panes of pale tinted glass with a few coloured ones.
- `victorian_circles`: Ruby circles in amber squares with cobalt accents, Victorian style.
- `amber_opalescent`: Large streaky opalescent amber and green pieces with thin copper foil.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `layout` | int | 0 | 0 to 2 | 0 irregular cathedral pieces, 1 diamond quarries, 2 circles in squares. |
| `pieces` | int | 6 | 2 to 16 | Panes across the tile. |
| `lead_width` | float | 0.06 | 0.015 to 0.15 | Width of the lead came as a share of a pane. |
| `streaks` | float | 0.5 | 0 to 1 | Streaks and density variation in the glass. |
| `seeds` | float | 0.4 | 0 to 1 | Tiny seed bubbles trapped in the glass. |
| `glow` | float | 0.85 | 0.1 to 1 | Brightness of the light through the glass in the emissive map. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo and the light in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`stained_glass.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python stained_glass.py --size 1024 --seed 7 --preset diamond_quarries --out textures/stained_glass
python stained_glass.py --width 512 --height 256 --set layout=2 --orm --out maps
```

`--orm` also writes `stained_glass_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import stained_glass

maps = stained_glass.generate(512, 512, seed=3, preset="diamond_quarries")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 31.1 s (14.3 s to compute, 16.9 s to write the PNG files) with a peak of about 806 MB; 256 x 256 takes about 2.2 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/stained_glass/` of your project (for example `python stained_glass.py --size 1024 --out path/to/project/baltor/textures/stained_glass`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion, emission and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo and emission are decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.004, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo and emissive with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `emissiveMap`.

For a window seen from inside, use the emissive map at full strength and keep scene lighting low on the glass; seen from outside in daylight, turn emission down and rely on the albedo and the smooth glass roughness.

## Limits

A flat panel without refraction, transmission depth or painted figures and grisaille. Glass colour, streaks and bubbles are stylized; streak directions come from a small set of whole-number vectors so they repeat across the tile edge. Solder blobs are drawn only where quarry leads cross. Backlighting is an emissive map of glass colour, not a light transport model, and the engine sets its strength. Occlusion is a blurred-height estimate.
