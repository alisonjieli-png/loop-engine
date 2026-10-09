# Fractal noise terrain with islands, ridges and terraces

Builds a square terrain whose heights come from fractal gradient noise: octaves of noise with rising frequency and falling amplitude. Ridged mode folds each octave into sharp crests, an island falloff lowers the edges, terraces quantise the height into soft steps, and everything below sea level is flattened to z = 0 and listed in the `sea` vertex group. With a base depth the sheet gets side walls and a bottom and becomes a closed solid.

## When to use it

Use it for landscapes, islands and mountain ranges in renders and games, as the base of a diorama, or with a base depth for a 3D printed relief. Use the `sea` group to place water or to mask a material.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `heightmap_terrain.py`.
2. Enable "Baltor Heightmap Terrain".
3. Run it from View3D > Add > Mesh > Heightmap Terrain. The operator is `baltor.heightmap_terrain`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python heightmap_terrain.py -- --resolution 128 --ridged true --terraces 8 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import heightmap_terrain
rows = heightmap_terrain.height_field(resolution=32, seed=9)
mesh = heightmap_terrain.build_geometry(resolution=32, seed=9, base_depth=1.0)
print(mesh["report"]["peak_m"])
```

Inside Blender, `heightmap_terrain.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `size` | float | 20.0 | 0.5 to 100000.0 | m | Side of the square terrain. |
| `resolution` | int | 64 | 2 to 1024 | count | Grid cells along each side. |
| `height` | float | 4.0 | 0.0 to 10000.0 | m | Height of the highest possible point above the lowest. |
| `feature_size` | float | 9.0 | 0.01 to 100000.0 | m | Width of the largest hills (one noise cell of the first octave). |
| `octaves` | int | 5 | 1 to 12 | count | Noise octaves. |
| `lacunarity` | float | 2.0 | 1.1 to 4.0 | ratio | Frequency multiplier per octave. |
| `gain` | float | 0.5 | 0.1 to 0.9 | ratio | Amplitude multiplier per octave. |
| `ridged` | bool | false | true or false | flag | Fold each octave as 1 - |noise| for sharp ridges. |
| `island` | float | 0.6 | 0.0 to 1.0 | ratio | Strength of the falloff that lowers the edges; 0 turns it off. |
| `terraces` | int | 0 | 0 to 64 | count | Number of terrace levels; 0 turns terracing off. |
| `sea_level` | float | 0.12 | 0.0 to 1.0 | ratio | Share of the height below which the ground is flattened. |
| `base_depth` | float | 0.0 | 0.0 to 10000.0 | m | Depth of side walls and a bottom below z = 0; 0 leaves an open sheet. |
| `seed` | int | 4 | 0 to 1000000 | seed | Random seed. |

## Outputs

One smooth-shaded mesh object named `Terrain` with a `UVMap` (0 to 1 over the square), a vertex group `sea` and the material `Baltor Terrain`, centred on the 3D cursor with sea level at z = 0. The core returns `vertices`, `faces`, `uv`, `groups` and a `report` with the peak height and the land share.

With the default parameters the core returns 4225 vertices, 4096 faces. The package tests pin these numbers.

## Limits

A height field: no caves, overhangs or erosion simulation. Gradient noise on a square lattice can show faint axis alignment. Terraces use a quartic softened step and island falloff a radial smoothstep, both stylized rather than geological. High resolutions are slow in pure Python (1024 cells per side is about a million vertices). Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Gradient (Perlin-style) noise with hashed gradients and quintic fade
- Fractal Brownian motion with lacunarity and gain
- Ridged multifractal fold 1 - |n|
- Radial smoothstep island falloff

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
