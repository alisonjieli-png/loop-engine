# L-shaped stairs with a landing or winders

Builds stairs that turn 90 degrees. The first flight climbs along +Y; the corner square is filled either with one landing slab or with three winders, wedge-shaped treads cut from the square by rays from the inner corner at 30 degree steps, each one rise higher. The second flight then continues to the right (+X) or the left (-X). A block under the corner can carry the turn down to the floor.

## When to use it

Use it in houses, towers and game levels where a stair has to wrap a wall corner. Winders save floor space; a landing gives a resting place and a safer turn.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `stairs_l_shaped.py`.
2. Enable "Baltor L-Shaped Stairs".
3. Run it from View3D > Add > Mesh > L-Shaped Stairs. The operator is `baltor.stairs_l_shaped`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python stairs_l_shaped.py -- --corner winders --turn left --first_steps 7 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import stairs_l_shaped
mesh = stairs_l_shaped.build_geometry(corner="landing", turn="left")
print(mesh["report"]["total_height_m"])
```

Inside Blender, `stairs_l_shaped.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `first_steps` | int | 6 | 1 to 60 | count | Treads in the first flight, along +Y. |
| `second_steps` | int | 5 | 1 to 60 | count | Treads in the second flight, after the turn. |
| `corner` | choice | `winders` | `landing`, `winders` | mode | Fill the corner with one landing or three winder treads. |
| `turn` | choice | `right` | `right`, `left` | mode | Direction of the second flight seen from the first. |
| `rise` | float | 0.18 | 0.05 to 0.4 | m | Height of one step, also between the landing and its neighbours. |
| `going` | float | 0.27 | 0.1 to 0.6 | m | Horizontal depth of one straight tread. |
| `width` | float | 0.9 | 0.3 to 6.0 | m | Width of both flights; the corner square has this side. |
| `tread_thickness` | float | 0.05 | 0.01 to 0.3 | m | Thickness of every tread and of the landing. |
| `support` | bool | true | true or false | flag | Add a block under the corner from the floor to the corner treads. |

## Outputs

One mesh object named `L-Shaped Stairs` with the material `Baltor Stair Concrete`, origin at the foot of the first flight on its centre line. The core returns `vertices`, `faces` and a `report` with the number of rises, the total height and the number of corner treads.

With the default parameters the core returns 116 vertices, 88 faces. The package tests pin these numbers.

## Limits

Winders radiate from the inner corner, so their inner ends are very narrow; real stairs often offset the pivot to keep a minimum inner tread, which this generator does not do. No stringers, risers or handrail. Parts are separate closed solids in one mesh. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Quarter-turn stair with three winders at 30 degree increments
- Ray and square intersection for winder outlines
- Mirroring a mesh with reversed face winding

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
