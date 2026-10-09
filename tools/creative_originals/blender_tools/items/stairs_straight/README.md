# Straight stair flight with stringers and a comfort report

Builds a straight flight of stairs climbing along +Y: one board per tread with the nosing overhanging the step below, optional riser boards, and two stringers whose top edge follows the nosing line and whose foot is cut level with the floor. Every part is a closed solid. The core also reports the pitch and the step formula 2R + G (twice the rise plus the going), which comfortable stairs keep between about 0.60 and 0.65 m.

## When to use it

Use it to place a stair between two floor levels quickly: divide the floor-to-floor height by a rise near 0.17 to 0.19 m to get the step count, then pick a going that keeps 2R + G in range. Suits buildings, decks, mezzanines and game levels.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `stairs_straight.py`.
2. Enable "Baltor Straight Stairs".
3. Run it from View3D > Add > Mesh > Straight Stairs. The operator is `baltor.stairs_straight`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python stairs_straight.py -- --steps 14 --rise 0.18 --going 0.27 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import stairs_straight
mesh = stairs_straight.build_geometry(steps=14, rise=0.18, going=0.27)
print(mesh["report"])  # pitch, 2R + G and whether it is in range
```

Inside Blender, `stairs_straight.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `steps` | int | 12 | 1 to 100 | count | Number of treads; the flight climbs steps times the rise. |
| `rise` | float | 0.175 | 0.05 to 0.4 | m | Height of one step. |
| `going` | float | 0.28 | 0.1 to 0.6 | m | Horizontal depth of one step, nosing to nosing. |
| `width` | float | 1.0 | 0.3 to 10.0 | m | Width of the treads between the stringers. |
| `tread_thickness` | float | 0.04 | 0.01 to 0.2 | m | Thickness of each tread board; must be less than the rise. |
| `nosing` | float | 0.025 | 0.0 to 0.1 | m | How far each tread overhangs the step below. |
| `risers` | bool | true | true or false | flag | Close each step with a vertical riser board. |
| `stringers` | bool | true | true or false | flag | Add a sloped stringer on each side. |
| `stringer_depth` | float | 0.25 | 0.05 to 1.0 | m | Vertical depth of each stringer below its top edge. |
| `stringer_thickness` | float | 0.04 | 0.01 to 0.2 | m | Thickness of each stringer board. |

## Outputs

One mesh object named `Straight Stairs` with the material `Baltor Stair Wood`, its origin at the foot of the flight on the centre line, and a custom property `baltor_two_rise_plus_going_m`. The core returns `vertices`, `faces` and a `report` with `rise_m`, `going_m`, `pitch_degrees`, `two_rise_plus_going_m` and `comfortable`.

With the default parameters the core returns 220 vertices, 162 faces. The package tests pin these numbers.

## Limits

The comfort report applies the common 2R + G rule of thumb (0.60 to 0.65 m) only; it is not a building code check, and codes differ by country and use. No handrail, landing or winder. Parts are separate closed solids in one mesh, touching but not merged. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Blondel step formula 2R + G
- Closed prisms from planar profiles with outward winding
- Sutherland-Hodgman clipping of the stringer outline against the floor plane

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
