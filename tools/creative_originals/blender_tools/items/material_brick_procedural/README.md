# Procedural brick material sized in metres

Creates a brick material where every size is in metres. Object coordinates are reordered so the courses lie in the chosen plane (a wall facing Y, a wall facing X, or a floor) and fed to Blender's Brick Texture with its scale fixed at 1, so the brick width, course height and mortar size you enter are real distances. The mortar mask raises the bricks with a bump and makes the mortar rougher, and a soft noise multiplies in grime.

## When to use it

Use it for building walls, chimneys, garden walls and brick paving when exact brick sizes matter but geometry per brick is too heavy. For bond patterns or real brick geometry use the brick wall generator instead.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_brick_procedural.py`.
2. Enable "Baltor Procedural Brick Material".
3. Run it from View3D > Object > Procedural Brick Material (with an object active). The operator is `baltor.material_brick_procedural`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_brick_procedural.py -- --orientation wall_xz --brick_width 0.3 --row_height 0.1 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_brick_procedural
graph = material_brick_procedural.material_graph(orientation="floor_xy")
print(material_brick_procedural.courses(2.4))  # whole courses in a 2.4 m wall
```

Inside Blender, `material_brick_procedural.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Brick` | any | text | Name of the new material. |
| `orientation` | choice | `wall_xz` | `wall_xz`, `wall_yz`, `floor_xy` | plane | Plane the courses lie in: rows run up the wall's Z, or along Y on a floor. |
| `brick_width` | float | 0.225 | 0.01 to 5.0 | m | Brick length plus one joint. |
| `row_height` | float | 0.075 | 0.005 to 2.0 | m | Course height plus one joint. |
| `mortar_size` | float | 0.01 | 0.0 to 0.2 | m | Mortar joint width. |
| `offset` | float | 0.5 | 0.0 to 1.0 | ratio | Shift of every other course as a share of the brick width. |
| `color_a` | vector | 0.42,0.12,0.06 | 0.0 to 1.0 | linear RGB | First brick colour. |
| `color_b` | vector | 0.3,0.1,0.06 | 0.0 to 1.0 | linear RGB | Second brick colour; bricks vary between the two. |
| `mortar_color` | vector | 0.5,0.48,0.44 | 0.0 to 1.0 | linear RGB | Mortar colour. |
| `grime` | float | 0.4 | 0.0 to 1.0 | ratio | How strongly the grime noise darkens the surface. |
| `bump` | float | 0.5 | 0.0 to 1.0 | ratio | Strength of the raised-brick bump. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Brick`) with 12 named nodes. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 12 nodes, 16 links. The package tests pin these numbers.

## Limits

Running bond with one offset only; English, Flemish and other bonds need the brick wall generator. Bricks are raised by bump, not displacement, so silhouettes stay flat. Object coordinates tie the pattern to the object's origin and scale. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Brick Texture node at unit scale so its sizes are object-space metres
- Swizzling object coordinates to orient a planar pattern
- Mortar mask driving bump and roughness

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
