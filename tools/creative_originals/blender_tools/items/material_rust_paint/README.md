# Rust over paint material with chipped edges

Creates a material for painted steel that has started to rust. A rust field adds a fractal noise to the cavity term 1 - AO, so rust starts in crevices and spreads in patches. Two thresholds on that field give nested masks: the rust itself and, just outside it, a thin ring where the paint has chipped off to bare steel. Paint, steel and rust are three Principled shaders combined by two mix shaders, and the rust gets its own colour variation and bump.

## When to use it

Use it on ships, cars, trains, machinery, railings, containers and anything painted that has been outside too long. Raise `coverage` for heavy decay and `cavity_weight` to keep rust in the seams.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_rust_paint.py`.
2. Enable "Baltor Rust Over Paint Material".
3. Run it from View3D > Object > Rust Over Paint Material (with an object active). The operator is `baltor.material_rust_paint`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_rust_paint.py -- --coverage 0.6 --cavity_weight 1.0 --paint_color 0.3,0.05,0.03 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_rust_paint
graph = material_rust_paint.material_graph(coverage=0.6)
print(material_rust_paint.thresholds(coverage=0.6))  # rust start, rust full, chip start
```

Inside Blender, `material_rust_paint.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Rusty Paint` | any | text | Name of the new material. |
| `paint_color` | vector | 0.05,0.2,0.12 | 0.0 to 1.0 | linear RGB | Colour of the paint. |
| `coverage` | float | 0.45 | 0.0 to 1.0 | ratio | How much of the surface rusts; 0 none, 1 nearly all. |
| `cavity_weight` | float | 0.6 | 0.0 to 2.0 | ratio | How strongly crevices (low ambient occlusion) attract rust. |
| `ao_distance` | float | 0.15 | 0.001 to 10.0 | m | Search distance of the ambient occlusion used for cavities. |
| `chip_width` | float | 0.05 | 0.0 to 0.3 | ratio | Width of the bare steel ring around rust, in units of the rust field. |
| `rust_scale` | float | 3.0 | 0.05 to 200.0 | 1/m | Frequency of the rust patches. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Rusty Paint`) with 16 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 16 nodes, 18 links. The package tests pin these numbers.

## Limits

The cavity term uses the Ambient Occlusion shader node, which Cycles evaluates by ray tracing and EEVEE approximates in screen space, so rust in crevices differs between them. Rust spreads by noise thresholds, not by any corrosion model, and has no streaks below edges. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Nested threshold masks from one scalar field for rust and chipped paint
- Ambient occlusion as a cavity mask
- Mixing three Principled shaders by masks

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
