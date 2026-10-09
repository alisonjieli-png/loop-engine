# Displaced icosphere rock with fractured facets

Builds a rock as one closed triangle mesh. The shape starts as an icosphere, every vertex moves along its radius by fractal value noise, a few random planes shear off flat facets like fractures, and the bottom is flattened so the rock sits on the ground. The seed fixes every random choice, so the same parameters always give the same rock.

## When to use it

Use it to make rocks, stones and boulders for environments, as varied sources for scattering, or as collision-friendly closed meshes. Raise `subdivisions` for close-up rocks and lower it for distant or low-poly ones.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `rock_displaced.py`.
2. Enable "Baltor Displaced Rock".
3. Run it from View3D > Add > Mesh > Displaced Rock. The operator is `baltor.rock_displaced`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python rock_displaced.py -- --seed 7 --subdivisions 4 --cuts 8 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import rock_displaced
mesh = rock_displaced.build_geometry(seed=7, subdivisions=4)
print(len(mesh["vertices"]))  # 10 * 4**4 + 2 = 2562
```

Inside Blender, `rock_displaced.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `seed` | int | 3 | 0 to 1000000 | seed | Random seed; the same seed gives the same rock. |
| `subdivisions` | int | 3 | 1 to 6 | count | Times each triangle is split in four (10 * 4^n + 2 vertices). |
| `radius` | float | 0.5 | 0.01 to 100.0 | m | Radius before noise and scaling. |
| `dimensions` | vector | 1.3,1.0,0.75 | 0.05 to 10.0 | ratio | Scale along X, Y and Z applied after the noise. |
| `roughness` | float | 0.35 | 0.0 to 0.9 | ratio | Largest radial displacement as a share of the radius. |
| `frequency` | float | 1.6 | 0.1 to 20.0 | 1/radius | Base frequency of the noise on the unit sphere. |
| `octaves` | int | 4 | 1 to 8 | count | Noise octaves; each doubles the frequency and halves the amplitude. |
| `cuts` | int | 5 | 0 to 20 | count | Random planes that shear off flat facets. |
| `cut_depth` | float | 0.18 | 0.0 to 0.6 | ratio | How deep each cut reaches, as a share of the radius. |
| `flat_base` | float | 0.25 | 0.0 to 0.9 | ratio | Share of the height below which vertices are flattened onto the base; 0 keeps it round. |
| `smooth` | bool | false | true or false | flag | Shade smooth instead of flat. |

## Outputs

One mesh object named `Rock` with a `UVMap` (spherical mapping) and the material `Baltor Rock`. The base sits at z = 0 under the 3D cursor. The core returns `vertices`, `faces` (triangles, counter-clockwise from outside), `uv`, `smooth` and the material slot.

With the default parameters the core returns 642 vertices, 1280 faces. The package tests pin these numbers.

## Limits

Displacement is radial, so overhangs and deep cracks cannot form. The noise is value noise on an integer lattice, which shows mild grid alignment at low octave counts. Strong cuts or a high flat base can produce long thin triangles. One material slot with a flat colour; no texture or weathering. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Icosphere by recursive four-way triangle subdivision projected to the sphere
- Value noise with quintic fade and integer hash lattice, fractal sum of octaves
- Planar cuts by projecting points beyond a half-space onto its plane
- Spherical UV mapping with seam correction per face

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
