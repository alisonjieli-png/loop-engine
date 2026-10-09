# Chain-link fence mesh

Galvanized steel, green vinyl-coated, fine rusty or black heavy-gauge chain link. Two families of wires run along the diagonals, a whole number of meshes across the tile, which makes the diamond openings and keeps the mesh periodic; distances to the nearest wire of each family give round wire profiles.

At every crossing one family passes over the other, alternating like a weave: the upper wire rises and the lower one dips as they approach (`knuckle`), which reads as the twisted knuckles of chain link. The albedo alpha is 1 on wire and 0 in the openings, and a vinyl coating (`coating`) turns the metal into a coloured dielectric.

## Maps

| Map | File | Channels | Colour space | Convention |
|---|---|---|---|---|
| `albedo` | `chain_link_fence_albedo.png` | 4 | sRGB | glTF base colour, values 0.03 to 0.95 |
| `normal` | `chain_link_fence_normal.png` | 3 | linear | tangent space, OpenGL (+Y up) |
| `roughness` | `chain_link_fence_roughness.png` | 1 | linear | 0 smooth, 1 rough, values 0.15 to 1 |
| `metallic` | `chain_link_fence_metallic.png` | 1 | linear | 0 dielectric, 1 metal |
| `height` | `chain_link_fence_height.png` | 1 | linear | white is high |
| `ao` | `chain_link_fence_ao.png` | 1 | linear | white is unoccluded |

Every map tiles: lattices, cells, distances and derivatives wrap around both edges.

## Presets

- `default`: Galvanized steel chain link.
- `green_vinyl`: Green vinyl-coated chain link with thicker wire.
- `rusty`: Old rusty chain link, fine mesh.
- `black_heavy`: Black coated heavy-gauge mesh with large openings.

## Parameters

| Name | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `meshes_across` | int | 6 | 2 to 24 | Diamond openings across the tile. |
| `wire` | float | 0.06 | 0.02 to 0.2 | Wire diameter as a share of the mesh spacing. |
| `knuckle` | float | 0.6 | 0 to 1 | How far wires rise and dip at the crossings. |
| `coating` | float | 0 | 0 to 1 | Vinyl coating (0 bare galvanized metal, 1 coated). |
| `rust` | float | 0 | 0 to 1 | Rust along the wires. |
| `hue_shift` | float | 0 | -0.5 to 0.5 | Hue rotation of the albedo in turns. |
| `saturation` | float | 1 | 0 to 2 | Albedo saturation multiplier. |
| `brightness` | float | 1 | 0.5 to 1 | Albedo brightness multiplier. |

A preset sets some parameters; keyword arguments override the preset. `generate()` raises `ValueError` for an unknown preset or parameter, a wrong type or a value outside its range.

## Generate the maps

`chain_link_fence.py` needs `texkit.py` and `pngio.py` beside it (both ship in this package) and the Python standard library only (3.10 or later).

```bash
python chain_link_fence.py --size 1024 --seed 7 --preset green_vinyl --out textures/chain_link_fence
python chain_link_fence.py --width 512 --height 256 --set meshes_across=24 --orm --out maps
```

`--orm` also writes `chain_link_fence_orm.png` (occlusion in red, roughness in green, metallic in blue). `--directx-normal` flips the green channel for engines that expect -Y normals. The command prints a JSON line with the files written and the time taken.

```python
import chain_link_fence

maps = chain_link_fence.generate(512, 512, seed=3, preset="green_vinyl")
albedo = maps["albedo"]  # {"channels": 3, "colour_space": "srgb", "pixels": bytes}
```

The pattern is defined in texture space, so a seed and preset keep their layout at any size.

## Cost

Measured on a shared build host with CPython 3.14.4: all maps at 1024 x 1024 take about 21.4 s (8.3 s to compute, 13.1 s to write the PNG files) with a peak of about 576 MB; 256 x 256 takes about 1.13 s. Time grows with the pixel count.

## Use in Godot 4

Generate the maps into `res://baltor/textures/chain_link_fence/` of your project (for example `python chain_link_fence.py --size 1024 --out path/to/project/baltor/textures/chain_link_fence`), let the editor import them, then assign `material.tres` to a mesh or copy it next to your scene. It is a `StandardMaterial3D` that reads every map from that folder: albedo, normal map, roughness, metallic, ambient occlusion and the height map, with parallax off. Change `uv1_scale` to repeat the tile. Transparency uses an alpha scissor at 0.5.

## Use in Blender

`blender_material.py` builds a Principled BSDF material from a folder of generated maps:

```python
import sys
sys.path.append("/path/to/this/package")
import blender_material
material = blender_material.build_material("/path/to/maps")
bpy.context.object.data.materials.append(material)
```

Albedo is decoded as sRGB and the other maps as Non-Color. The normal map goes through a Normal Map node (strength 1) and the height map through a Displacement node (scale 0.003, midlevel 0.5) set to true displacement, which needs a subdivided mesh to show.

## Use in glTF and three.js

glTF 2.0: albedo is `baseColorTexture`, the normal map is `normalTexture` (OpenGL convention, as glTF expects), and the `--orm` file serves as both `metallicRoughnessTexture` (green roughness, blue metallic) and `occlusionTexture` (red). three.js: load albedo with `colorSpace = SRGBColorSpace` and the others as linear data, set `wrapS` and `wrapT` to `RepeatWrapping`, and use `MeshStandardMaterial` with `map`, `normalMap`, `roughnessMap`, `metalnessMap`, `aoMap` and optionally `displacementMap` and `alphaTest: 0.5`.

## Limits

Wires are straight diagonals with knuckles suggested by height at the crossings, not the helical twist of real woven wire. The openings need alpha scissor, and at a distance mipmapped alpha thins the mesh. Occlusion is a blurred-height estimate, not ray traced.
