# Brick wall in English, Flemish and other bonds

Builds a wall brick by brick. Each bond is a rule for one course: stretcher bond shifts every other course by half a brick, English bond alternates two-leaf stretcher courses with header courses that start with a queen closer, Flemish bond alternates headers and stretchers within each course, and common bond inserts a header course every few courses. Bricks that cross the wall ends are cut, every brick is a closed box, and a recessed mortar core shows in the joints. Three brick colours are spread over the bricks by a seeded hash.

## When to use it

Use it when brick walls are seen up close and a flat texture is not enough: ruins, garden walls, building blockouts, destructible walls or reference for bond patterns. The report gives brick counts per type and per square metre of face.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `brick_wall_bonds.py`.
2. Enable "Baltor Brick Wall Bonds".
3. Run it from View3D > Add > Mesh > Brick Wall. The operator is `baltor.brick_wall_bonds`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python brick_wall_bonds.py -- --bond flemish --length 3 --courses 20 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import brick_wall_bonds
wall = brick_wall_bonds.build_geometry(bond="flemish", length=3.0, courses=20)
print(wall["report"]["bricks"], wall["report"]["headers"])
```

Inside Blender, `brick_wall_bonds.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `bond` | choice | `english` | `stretcher`, `stack`, `english`, `flemish`, `common` | pattern | Bond pattern. |
| `length` | float | 2.0 | 0.3 to 30.0 | m | Wall length along +X. |
| `courses` | int | 12 | 1 to 200 | count | Number of brick courses. |
| `brick` | vector | 0.215,0.1025,0.065 | 0.01 to 1.0 | m | Brick length, width and height. |
| `joint` | float | 0.01 | 0.002 to 0.05 | m | Mortar joint thickness. |
| `header_every` | int | 6 | 2 to 12 | count | Common bond: one header course in every this many courses. |
| `recess` | float | 0.006 | 0.0 to 0.03 | m | How far the mortar core sits behind the brick faces. |
| `seed` | int | 1 | 0 to 1000000 | seed | Seed for the spread of the three brick colours. |

## Outputs

One mesh object named `Brick Wall` with four material slots (mortar and three brick colours), front face at y = 0, starting at x = 0. The core returns `vertices`, `faces`, `face_materials`, the material list and a `report` with counts of stretchers, headers, closers and cut bricks, the wall thickness and bricks per square metre.

With the default parameters the core returns 1784 vertices, 1338 faces. The package tests pin these numbers.

## Limits

Straight walls only; no openings, corners that interlock with a return wall, arches or chamfers. Bricks are sharp boxes without bevels. The mortar is a recessed core box, not tooled joint profiles. Brick sizes default to UK metric bricks; set others with the brick parameter. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Masonry bonds: stretcher, stack, English, Flemish and common (American)
- Queen closer to offset header courses by a quarter brick
- Seeded integer hash to assign material slots

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
