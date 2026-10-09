# Wireframe overlay material

Creates a material that draws the mesh's edges into the render. The Wireframe node gives 1 on edges with a width in pixels or in metres, and that value mixes a base Principled surface with an emission shader in the line colour. A facing term can fade lines on surfaces seen edge-on so dense meshes stay readable.

## When to use it

Use it to present topology in portfolio renders, for technical and blueprint looks, for sci-fi scanning effects and to check mesh density in a final render.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_wireframe_overlay.py`.
2. Enable "Baltor Wireframe Overlay Material".
3. Run it from View3D > Object > Wireframe Overlay Material (with an object active). The operator is `baltor.material_wireframe_overlay`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_wireframe_overlay.py -- --line_width 1.5 --line_color 1,0.5,0.1 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_wireframe_overlay
graph = material_wireframe_overlay.material_graph(use_pixel_size=False, line_width=0.01)
print(material_wireframe_overlay.line_mix(1.0, 0.0))  # 1.0 on an edge seen face on
```

Inside Blender, `material_wireframe_overlay.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Wireframe` | any | text | Name of the new material. |
| `line_color` | vector | 0.2,0.9,1.0 | 0.0 to 1.0 | linear RGB | Colour of the edge lines. |
| `surface_color` | vector | 0.02,0.03,0.05 | 0.0 to 1.0 | linear RGB | Colour of the faces between the lines. |
| `line_width` | float | 1.2 | 0.01 to 100.0 | px or m | Line width in pixels, or in metres when use_pixel_size is false. |
| `use_pixel_size` | bool | true | true or false | flag | Measure the line width in pixels on screen instead of metres on the surface. |
| `line_strength` | float | 3.0 | 0.0 to 1000.0 | ratio | Emission strength of the lines. |
| `fade_grazing` | float | 0.4 | 0.0 to 1.0 | ratio | How much lines fade on surfaces seen edge-on. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Wireframe`) with 8 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 8 nodes, 7 links. The package tests pin these numbers.

## Limits

Relies on the Wireframe shader node, which Cycles renders; EEVEE does not support it and shows the base surface only. Edges come from the triangulated render mesh, so n-gons show their internal triangulation. Lines are emissive and do not cast shadows. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Wireframe shader node in pixel or world size
- Facing term to fade lines at grazing angles
- Mix of a surface and an emission

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
