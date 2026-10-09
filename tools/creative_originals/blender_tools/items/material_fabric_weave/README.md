# Plain-weave fabric material with thread bump

Creates a woven fabric material. UV coordinates are scaled by the thread count, and in every cell the parity of floor(u) + floor(v) decides whether the warp or the weft thread lies on top: the over-under pattern of a plain weave. Each visible thread has a rounded profile sin(pi * f) across its width that drives a bump and darkens the thread edges, and the parity picks the warp or weft colour. A Principled sheen lobe gives the soft rim of cloth.

## When to use it

Use it for shirts, canvas, upholstery, tablecloths, flags and sacks, on any mesh with a UV map. Raise `threads` for fine fabric seen from afar and lower it for coarse weaves close up.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_fabric_weave.py`.
2. Enable "Baltor Fabric Weave Material".
3. Run it from View3D > Object > Fabric Weave Material (with an object active). The operator is `baltor.material_fabric_weave`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_fabric_weave.py -- --threads 200 --warp_color 0.4,0.05,0.05 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_fabric_weave
graph = material_fabric_weave.material_graph(threads=200)
print(material_fabric_weave.weave_at(0.0025, 0.001, threads=200))  # ('warp', ...)
```

Inside Blender, `material_fabric_weave.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Fabric` | any | text | Name of the new material. |
| `threads` | float | 60.0 | 1.0 to 5000.0 | 1/uv | Threads per UV unit in each direction. |
| `warp_color` | vector | 0.12,0.2,0.45 | 0.0 to 1.0 | linear RGB | Colour of the warp threads (along V). |
| `weft_color` | vector | 0.6,0.55,0.45 | 0.0 to 1.0 | linear RGB | Colour of the weft threads (along U). |
| `sheen` | float | 0.6 | 0.0 to 1.0 | ratio | Sheen weight of the Principled BSDF. |
| `bump` | float | 0.35 | 0.0 to 1.0 | ratio | Strength of the thread bump. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Fabric`) with 19 named nodes that read the UV map. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 19 nodes, 23 links. The package tests pin these numbers.

## Limits

Plain weave only; twill, satin and knits are not modelled. Threads are straight and evenly spaced with no fibre fuzz, slubs or irregularity. The pattern follows the UV map, so it needs reasonable UVs and aliases when threads are smaller than a pixel. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Plain weave by parity of floor(u) + floor(v)
- Thread profile sin(pi * f)
- Sheen lobe of the Principled BSDF for cloth

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
