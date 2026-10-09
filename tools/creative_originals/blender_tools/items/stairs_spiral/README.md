# Spiral staircase generator

Builds a spiral staircase as one mesh: wedge-shaped tread slabs that climb around a central column, one square baluster per tread and a square handrail that follows the helix of the tread nosings. Every part is a closed solid with outward normals, and every face has box projected UVs at one UV unit per metre.

## When to use it

Use it when a scene needs a believable spiral stair quickly: towers, lighthouses, lofts, industrial platforms or game level blockouts. The rise per step is the total height divided by the step count, so set those two from the floor heights you have.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `stairs_spiral.py`.
2. Enable "Baltor Spiral Stairs".
3. Run it from View3D > Add > Mesh > Spiral Stairs. The operator is `baltor.stairs_spiral`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python stairs_spiral.py -- --steps 18 --total_height 3.2 --turn_degrees 270 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import stairs_spiral
mesh = stairs_spiral.build_geometry(steps=18, total_height=3.2, turn_degrees=270)
print(len(mesh["vertices"]), len(mesh["faces"]))
```

Inside Blender, `stairs_spiral.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `steps` | int | 16 | 3 to 120 | count | Number of treads. |
| `total_height` | float | 3.0 | 0.5 to 20.0 | m | Floor to the top of the last tread. |
| `turn_degrees` | float | 360.0 | 30.0 to 1440.0 | degree | Total rotation from the first tread to the end of the last. |
| `inner_radius` | float | 0.15 | 0.05 to 2.0 | m | Radius of the central column, where the treads start. |
| `outer_radius` | float | 1.1 | 0.3 to 6.0 | m | Outer radius of the treads; must exceed inner_radius by at least 0.2 m. |
| `tread_thickness` | float | 0.05 | 0.01 to 0.3 | m | Thickness of each tread slab. |
| `arc_segments` | int | 2 | 1 to 12 | count | Segments along the outer arc of each tread and of the handrail per tread. |
| `column_sides` | int | 16 | 3 to 64 | count | Sides of the central column prism. |
| `handrail` | bool | true | true or false | flag | Add a square-section helical handrail and one baluster per tread. |
| `rail_height` | float | 0.9 | 0.5 to 1.5 | m | Height of the handrail above the tread nosing line. |
| `clockwise` | bool | false | true or false | flag | Climb clockwise seen from above instead of counter-clockwise. |

## Outputs

One mesh object named `Spiral Stairs`, origin at the base of the column and placed at the 3D cursor, with a `UVMap` layer. The core returns `vertices` (metres), `faces` (vertex indices, counter-clockwise seen from outside) and `uv` (one pair per face corner).

With the default parameters the core returns 484 vertices, 404 faces. The package tests pin these numbers.

## Limits

One mesh object made of separate closed solids that touch but are not merged, so booleans need a merge first. The handrail is a square section swept along the helix with the section kept vertical, not a circular profile, and the balusters are square posts. Treads are flat slabs with no nosing profile. No building code check is made. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Annular sector solids with outward counter-clockwise winding
- Helix sweep of a square section in the radial and vertical frame
- Box projection UVs by dominant normal axis at one unit per metre

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
