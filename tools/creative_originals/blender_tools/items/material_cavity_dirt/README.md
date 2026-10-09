# Cavity dirt material with vertical streaks

Creates a material that gets dirty where dirt would gather. The Ambient Occlusion node finds crevices, corners and overhangs, and 1 - AO turns them into a cavity term. A noise stretched strongly along Z adds vertical streaks. The sum is thresholded by the dirt amount into a soft mask that darkens the base colour toward the dirt colour and raises the roughness.

## When to use it

Use it on stone and concrete buildings, statues, engines, kitchen props and old furniture, or as a quick grime pass on any model with crevices.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_cavity_dirt.py`.
2. Enable "Baltor Cavity Dirt Material".
3. Run it from View3D > Object > Cavity Dirt Material (with an object active). The operator is `baltor.material_cavity_dirt`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_cavity_dirt.py -- --dirt_amount 0.6 --streaks 0.5 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_cavity_dirt
graph = material_cavity_dirt.material_graph(dirt_amount=0.6)
print(material_cavity_dirt.dirt_mask(0.2, 0.5))  # deep crevice: dirty
```

Inside Blender, `material_cavity_dirt.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Cavity Dirt` | any | text | Name of the new material. |
| `base_color` | vector | 0.7,0.68,0.62 | 0.0 to 1.0 | linear RGB | Colour of the clean surface. |
| `dirt_color` | vector | 0.09,0.07,0.05 | 0.0 to 1.0 | linear RGB | Colour of the dirt. |
| `ao_distance` | float | 0.3 | 0.001 to 50.0 | m | How far the occlusion looks for nearby geometry. |
| `dirt_amount` | float | 0.5 | 0.0 to 1.0 | ratio | How much of the surface the dirt reaches. |
| `streaks` | float | 0.35 | 0.0 to 1.0 | ratio | Weight of the vertical streaks. |
| `streak_scale` | float | 6.0 | 0.1 to 500.0 | 1/m | Frequency of the streaks across the surface. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Cavity Dirt`) with 11 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 11 nodes, 11 links. The package tests pin these numbers.

## Limits

Cavities come from the Ambient Occlusion shader node: ray traced in Cycles, screen-space approximated in EEVEE, so results differ. Streaks follow object Z and do not know about ledges or drip sources. Dirt is colour and roughness only, without bump. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Ambient occlusion as a cavity mask (1 - AO)
- Anisotropic noise by scaling one axis of the coordinates
- Soft threshold by map range

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
