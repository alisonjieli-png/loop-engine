# Parametric table with tapered, round or turned legs

Builds a table from its overall size. The top is a rounded rectangle extruded to its thickness, the four legs are set in from the corners, and aprons join the legs under the top, set back slightly from the legs' outer faces. Legs can be tapered square frustums, slightly tapered cylinders, or turned legs with beads and a square block where the apron meets them. Every part is a closed solid.

## When to use it

Use it to furnish interiors, kitchens and offices quickly, as a product display surface, or as a blockout to replace later. Standard dining tables are about 0.75 m high.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `table_parametric.py`.
2. Enable "Baltor Parametric Table".
3. Run it from View3D > Add > Mesh > Parametric Table. The operator is `baltor.table_parametric`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python table_parametric.py -- --length 2.0 --width 1.0 --leg_style turned --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import table_parametric
mesh = table_parametric.build_geometry(length=2.0, leg_style="turned")
print(len(mesh["vertices"]), len(mesh["faces"]))
```

Inside Blender, `table_parametric.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `length` | float | 1.6 | 0.3 to 10.0 | m | Length of the top along X. |
| `width` | float | 0.9 | 0.3 to 5.0 | m | Width of the top along Y. |
| `height` | float | 0.75 | 0.2 to 2.0 | m | Floor to the top surface. |
| `top_thickness` | float | 0.035 | 0.008 to 0.2 | m | Thickness of the top. |
| `corner_radius` | float | 0.06 | 0.0 to 2.5 | m | Radius of the rounded top corners; 0 for square corners. |
| `leg_style` | choice | `tapered` | `tapered`, `round`, `turned` | style | Leg shape. |
| `leg_size` | float | 0.06 | 0.015 to 0.4 | m | Width of the legs at the top. |
| `leg_inset` | float | 0.05 | 0.0 to 1.0 | m | Distance from the top's edge to the legs' outer faces. |
| `apron_height` | float | 0.09 | 0.0 to 0.5 | m | Height of the aprons under the top; 0 leaves them out. |
| `corner_segments` | int | 6 | 1 to 32 | count | Segments per rounded corner and per quarter of a round leg. |

## Outputs

One mesh object named `Table` with the material `Baltor Table Wood`, standing on z = 0 and centred under the 3D cursor. The core returns `vertices`, `faces`, `smooth` and the material.

With the default parameters the core returns 120 vertices, 78 faces. The package tests pin these numbers.

## Limits

Four-legged rectangular tables only; no pedestal, drawers, stretchers or joinery detail. Turned legs use one fixed bead profile scaled to the leg size. Parts touch but are not merged, and edges are sharp without bevels. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Rounded rectangle from quarter-circle corners
- Lofting closed solids through rings of equal vertex count
- Square ring with matching vertex count by projecting angles onto the square

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
