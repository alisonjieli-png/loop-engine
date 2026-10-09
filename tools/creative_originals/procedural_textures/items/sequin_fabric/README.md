# Sequin and paillette fabric

Gold sequins on black mesh, sparkling silver, holographic foil, small gunmetal sequins or large rose-gold paillettes. Sequins sit in rows with whole counts across and down the tile and odd rows shift by half a sequin, so the discs pack like scales and the fabric tiles.

`rows` sets the sequin count and `size` how far neighbours overlap. Every sequin slopes up toward its free lower edge, `cup` dishes its face, `tilt` gives it a random tilt so neighbours catch light differently, and `hole` opens the centre to the backing and thread. The metallic map marks the sequins as metal and the backing as cloth; `rainbow` turns the colour of each sequin with its tilt direction and across its face, as holographic foil does.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `sequin_fabric_albedo.png` | 3 | sRGB | glTF base colour, values 0.02 to 0.95 |
| `normal` | `sequin_fabric_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `sequin_fabric_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.08 to 1 |
| `metallic` | `sequin_fabric_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `sequin_fabric_height.png` | 1 | linear | white is high |
| `ao` | `sequin_fabric_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Gold sequins packed like scales on black mesh.
- `silver_party`: Silver sequins with strong random tilts for a lot of sparkle.
- `holographic`: Holographic foil sequins whose colour changes with the tilt.
- `black_gunmetal`: Small gunmetal sequins lying flat in tight rows.
- `paillettes_rose`: Large rose-gold paillettes with small holes and a wide overlap.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `rows` | int | 18 | 6 to 40 | Rows of sequins down the tile; as many sequins run across each row. |
| `size` | float | 1.35 | 1 to 1.8 | Sequin diameter as a multiple of the row spacing: the overlap between neighbours. |
| `tilt` | float | 0.45 | 0 to 1 | Random tilt of each sequin, which makes them sparkle differently. |
| `hole` | float | 0.16 | 0 to 0.35 | Radius of the centre hole as a share of the sequin radius (0 for no hole). |
| `cup` | float | 0.4 | 0 to 1 | How dished (cupped) each sequin is. |
| `rainbow` | float | 0 | 0 to 1 | Holographic foil: colour turning with each sequin's tilt direction and across its face. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`sequin_fabric.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python sequin_fabric.py --size 1024 --seed 7 --preset silver_party --out textures/sequin_fabric
python sequin_fabric.py --width 512 --height 256 --set rows=40 --orm --out maps
```

`--orm` also writes `sequin_fabric_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import sequin_fabric

maps = sequin_fabric.generate(512, 512, seed=3, preset="silver_party")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 20.6 s (10.9 s to compute, 9.7 s to write the PNG files) with a peak of about 514 MB; 256 x 256 takes about 1.39 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/sequin_fabric/` of your project (for example `python sequin_fabric.py --size 1024 --out path/to/project/baltor/textures/sequin_fabric`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile.

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

Sequins are flat discs with a sloped and dished height, one layer per row in a fixed overlap order; there is no stitching thread across the face, no loose or flipped sequins and no reversible two-tone sequins. Sparkle comes from per-sequin normal tilt in the normal map, so it depends on the renderer's lights and reflections. Holographic colour is a hue wheel driven by tilt direction, a stylized stand-in for diffraction, and does not change with view angle. Occlusion is a blurred-height estimate, not ray traced.
