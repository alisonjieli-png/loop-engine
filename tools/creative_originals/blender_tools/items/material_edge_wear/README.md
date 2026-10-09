# Edge wear material from the Bevel node

Creates a painted metal material whose edges look handled. The Bevel shader node returns a normal rounded over a radius; on flat areas it matches the true normal, and near edges it bends away. The edge term 1 - dot(bevel normal, true normal), scaled by the sensitivity, is multiplied by a fractal noise and thresholded, so the wear breaks into chips. The mask mixes a painted Principled shader with a bare metal one, and the paint uses the rounded normal so edges catch a soft highlight.

## When to use it

Use it on tools, toolboxes, vehicles, weapons, machines and furniture rendered in Cycles, where worn edges sell age and use without hand-painted masks.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_edge_wear.py`.
2. Enable "Baltor Edge Wear Material".
3. Run it from View3D > Object > Edge Wear Material (with an object active). The operator is `baltor.material_edge_wear`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_edge_wear.py -- --wear_width 0.04 --wear_amount 0.6 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_edge_wear
graph = material_edge_wear.material_graph(wear_amount=0.6)
print(material_edge_wear.wear_mask(1.0, 0.9))  # 0.0 on a flat area
```

Inside Blender, `material_edge_wear.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Edge Wear` | any | text | Name of the new material. |
| `paint_color` | vector | 0.6,0.38,0.03 | 0.0 to 1.0 | linear RGB | Colour of the paint. |
| `metal_color` | vector | 0.62,0.62,0.6 | 0.0 to 1.0 | linear RGB | Colour of the bare metal under the paint. |
| `wear_width` | float | 0.12 | 0.0005 to 2.0 | m | Bevel radius: how far from an edge wear can reach. |
| `sensitivity` | float | 0.12 | 0.005 to 1.0 | ratio | Edge term (1 - dot) that counts as fully on the edge. |
| `wear_amount` | float | 0.65 | 0.0 to 1.0 | ratio | How much of the edge zone wears through. |
| `noise_scale` | float | 18.0 | 0.1 to 1000.0 | 1/m | Frequency of the chip noise. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Edge Wear`) with 13 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 13 nodes, 13 links. The package tests pin these numbers.

## Limits

Relies on the Bevel shader node, which only Cycles evaluates; EEVEE returns the plain normal, so no wear appears there. Detects convex and concave edges alike within the radius. Noise-based chips, not a wear simulation. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Bevel shader normal versus true normal as an edge detector
- Noise-modulated threshold for chipped wear
- Mix shader between paint and metal

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
