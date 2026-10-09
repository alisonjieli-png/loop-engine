# Frost ferns growing on window glass

Fern frost with feathered plumes, dense straight needles with short spurs, large plumes packed edge to edge, or heavy rime haze with small crystals. Seeds keep a minimum spacing on the torus. From each, a main stem walks forward with a slight random curl and puts out opposite side branches at about 60 degrees, the hexagonal habit of ice; branches grow the same way at a smaller scale down to `levels`, and they shorten toward the tip of their parent, which gives the plume its feather outline.

Every segment is painted as a capsule with wrap-around into a coverage field, softened by a blurred copy so plumes read as feathery, and fine rime haze fills in between. The albedo alpha is nearly opaque on frost and nearly transparent on glass; frost is raised and rough, glass flat and smooth, so the normal and roughness maps also work on an opaque window material.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `frost_ferns_albedo.png` | 4 | sRGB | glTF base colour, values 0.3 to 1 |
| `normal` | `frost_ferns_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `frost_ferns_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.04 to 0.95 |
| `height` | `frost_ferns_height.png` | 1 | linear | white is high |
| `ao` | `frost_ferns_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Fern frost: feathered plumes spreading across a window.
- `needle_frost`: Dense straight needles with short spurs crossing at random.
- `feathered`: Large dense plumes with sub-branches packed edge to edge.
- `hoar_haze`: Heavy rime haze with small sparse crystals, almost fogged over.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `crystals` | int | 9 | 2 to 30 | Crystal seeds in the tile (about; seeds keep a minimum spacing). |
| `size` | float | 0.4 | 0.08 to 0.5 | Length of a main stem in texture units. |
| `branching` | float | 0.85 | 0 to 1 | Chance of side branches at each step of a stem or branch. |
| `levels` | int | 3 | 1 to 3 | Branching depth: 1 bare needles, 2 branches, 3 branches with sub-branches. |
| `curl` | float | 0.4 | 0 to 1 | How much stems wander: 0 straight needles, 1 curling plumes. |
| `thickness` | float | 1 | 0.5 to 2 | Width of the crystal lines. |
| `haze` | float | 0.25 | 0 to 1 | Fine rime haze between the crystals. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1.5 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`frost_ferns.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python frost_ferns.py --size 1024 --seed 7 --preset needle_frost --out textures/frost_ferns
python frost_ferns.py --width 512 --height 256 --set crystals=30 --orm --out maps
```

`--orm` also writes `frost_ferns_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import frost_ferns

maps = frost_ferns.generate(512, 512, seed=3, preset="needle_frost")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 21.1 s (9.6 s to compute, 11.6 s to write the PNG files) with a peak of about 682 MB; 256 x 256 takes about 1.79 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/frost_ferns/` of your project (for example `python frost_ferns.py --size 1024 --out path/to/project/baltor/textures/frost_ferns`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses alpha blending, so the material sorts with other transparent surfaces.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 0.6) and the height map through a Displacement node (scale 0.002, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `aoMap` and optionally `displacementMap` and `transparent: true`.

In Godot the template uses alpha blending; put it on a quad just in front of the window glass, or use the albedo alpha as a mask in a glass shader.

## Limits

Growth is a stylized branching walk, not a diffusion-limited crystal growth simulation, so plumes are self-similar sketches of real fern frost. Crystals grow from scattered seeds rather than from the edges and scratches where frost usually starts. Branches finer than a pixel at the output size are skipped, so small outputs show the main plumes only. The alpha suits blending over a window; it does not model refraction or light scattering in the ice, and engines sort alpha-blended surfaces with other transparent ones.
