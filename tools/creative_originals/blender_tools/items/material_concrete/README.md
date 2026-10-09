# Cast concrete material with pores and board seams

Creates a concrete material from four layers on object coordinates: large water stains from a slow noise and a colour ramp, aggregate specks where a Voronoi cell distance is small, fine air pores that are darkened and pushed in by a bump, and, when board lines are on, thin dark seams every board width up the object's Z axis where formwork boards met.

## When to use it

Use it for brutalist buildings, parking garages, bunkers, stairs, floors and sidewalks, or any large cast surface that should not look like a flat grey.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `material_concrete.py`.
2. Enable "Baltor Concrete Material".
3. Run it from View3D > Object > Concrete Material (with an object active). The operator is `baltor.material_concrete`; its redo panel shows every parameter listed below.

### As a script

```
blender --background scene.blend --python material_concrete.py -- --board_lines true --board_width 0.2 --pore_depth 0.5 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

In script mode the material goes on the active object of the opened file.

### From Python

The core needs no Blender:

```python
import material_concrete
graph = material_concrete.material_graph(board_lines=False)
print(len(graph["trees"][0]["nodes"]))  # 13 without board seams
```

Inside Blender, `material_concrete.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `material_name` | string | `Baltor Concrete` | any | text | Name of the new material. |
| `color` | vector | 0.3,0.29,0.27 | 0.0 to 1.0 | linear RGB | Base colour of the cement. |
| `stain_strength` | float | 0.7 | 0.0 to 1.0 | ratio | Contrast of the large water stains. |
| `aggregate_scale` | float | 60.0 | 1.0 to 2000.0 | 1/m | Aggregate cells per metre. |
| `aggregate_amount` | float | 0.25 | 0.0 to 0.6 | ratio | Radius of the aggregate specks as a share of a cell. |
| `pore_scale` | float | 260.0 | 5.0 to 5000.0 | 1/m | Pore cells per metre. |
| `pore_depth` | float | 0.35 | 0.0 to 1.0 | ratio | Strength of the pore bump. |
| `board_lines` | bool | true | true or false | flag | Add horizontal seams from board formwork. |
| `board_width` | float | 0.15 | 0.02 to 2.0 | m | Height of one formwork board. |
| `assign` | bool | true | true or false | flag | Assign the material to the active object. |

## Outputs

A material named by `material_name` (default `Baltor Concrete`) with 13 named nodes, or 18 with board lines. When `assign` is true it replaces the material slots of the active object; otherwise it keeps a fake user. The core returns the tree as `trees[0]`.

With the default parameters the core returns 18 nodes, 21 links. The package tests pin these numbers.

## Limits

Pores and aggregate come from Voronoi cells, which are evenly spread rather than graded like real aggregate. Board seams are horizontal only (along object Z) and carry no wood grain imprint. No cracks or spalling. Rendered here with Cycles CPU only. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Voronoi F1 distance thresholds for specks and pores
- Low-frequency noise through a colour ramp for stains
- Periodic seams from the fractional part of height over board width

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
