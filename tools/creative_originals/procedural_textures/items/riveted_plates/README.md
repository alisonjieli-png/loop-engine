# Riveted metal plates

Grey painted ship hull plating, bare brass with copper rivets, aluminium aircraft skin or a dark rusty iron tank. The tile is a grid of plates; each plate sits at its own small height, so every seam shows a step as in lapped plating, and each takes its own tone.

Rivets run in rows just inside every plate edge, as domed heads or, with a low `rivet_height`, nearly flush heads for airframes. Rust or dirt streaks run down from each rivet: every column is swept downward with a fading trail, twice around so the trail wraps. Paint wears through on the rivet heads and plate edges first.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `riveted_plates_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `riveted_plates_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `riveted_plates_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.12 to 1 |
| `metallic` | `riveted_plates_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `riveted_plates_height.png` | 1 | linear | white is high |
| `ao` | `riveted_plates_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Grey painted ship hull plating with rust streaks.
- `steampunk_brass`: Bare brass plates with copper rivets.
- `airframe`: Aluminium aircraft skin with flush rivets.
- `rusty_tank`: Dark iron tank with heavy rust runs.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `plates_across` | int | 2 | 1 to 8 | Plates across the tile. |
| `plate_rows` | int | 2 | 1 to 8 | Plate rows down the tile. |
| `rivets_per_edge` | int | 9 | 2 to 30 | Rivets along each plate edge. |
| `rivet_size` | float | 0.012 | 0.003 to 0.03 | Rivet head radius in texture units. |
| `rivet_height` | float | 0.8 | 0.05 to 1 | Rivet head height (low values give flush rivets). |
| `paint` | float | 1 | 0 to 1 | Paint coverage (0 bare metal plates). |
| `streaks` | float | 0.4 | 0 to 1 | Rust or dirt streaks below the rivets. |
| `plate_variation` | float | 0.4 | 0 to 1 | Tone difference between plates. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`riveted_plates.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python riveted_plates.py --size 1024 --seed 7 --preset steampunk_brass --out textures/riveted_plates
python riveted_plates.py --width 512 --height 256 --set plates_across=8 --orm --out maps
```

`--orm` also writes `riveted_plates_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import riveted_plates

maps = riveted_plates.generate(512, 512, seed=3, preset="steampunk_brass")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 18.9 s (10.5 s to compute, 8.4 s to write the PNG files) with a peak of about 630 MB; 256 x 256 takes about 1.35 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/riveted_plates/` of your project (for example `python riveted_plates.py --size 1024 --out path/to/project/baltor/textures/riveted_plates`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap`.

## Limits

Plates form a regular grid; real plating staggers its seams and follows frames and curvature. Rivets run in straight rows just inside each edge. Streaks always run toward the bottom of the tile. Occlusion is a blurred-height estimate, not ray traced.
