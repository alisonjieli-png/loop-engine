# Helical compression spring with spring rate

Builds a helical compression spring: a round wire swept along a helix whose closed end coils climb one wire diameter per turn (so the wires touch) and whose active coils climb by the pitch. The wire section follows the helix without twisting and both ends are capped, so the spring is one closed solid. The report gives the free length, the solid length, the spring index and the rate k = G d^4 / (8 D^3 n).

## When to use it

Use it for suspension parts, pens, valves, toys and machine props, and when the stiffness of a spring of given size and material matters, for example to drive a matching animation.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `coil_spring.py`.
2. Enable "Baltor Coil Spring".
3. Run it from View3D > Add > Mesh > Coil Spring. The operator is `baltor.coil_spring`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python coil_spring.py -- --active_coils 8 --pitch 0.012 --wire_diameter 0.003 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import coil_spring
print(coil_spring.report(active_coils=8, pitch=0.012))
mesh = coil_spring.build_geometry(active_coils=8)
```

Inside Blender, `coil_spring.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `mean_diameter` | float | 0.04 | 0.002 to 5.0 | m | Mean coil diameter D, centre of wire to centre of wire. |
| `wire_diameter` | float | 0.004 | 0.0002 to 0.5 | m | Wire diameter d. |
| `active_coils` | float | 6.0 | 0.5 to 200.0 | turns | Active coils n between the closed ends. |
| `pitch` | float | 0.011 | 0.0002 to 2.0 | m | Rise per active coil; must exceed the wire diameter. |
| `end_coils` | float | 1.0 | 0.0 to 5.0 | turns | Closed coils at each end, climbing one wire diameter per turn. |
| `clockwise` | bool | false | true or false | flag | Left-hand winding instead of right-hand. |
| `samples_per_turn` | int | 28 | 6 to 128 | count | Sweep samples per turn. |
| `wire_sides` | int | 10 | 3 to 48 | count | Sides of the round wire section. |
| `shear_modulus` | float | 79300000000.0 | 1000000.0 to 500000000000.0 | Pa | Shear modulus G of the wire material (spring steel is about 79.3 GPa). |

## Outputs

One smooth-shaded mesh object named `Coil Spring` with the material `Baltor Spring Steel`, axis along +Z from z = 0, and a custom property `baltor_spring_rate_n_per_m`. The core returns `vertices`, `faces`, `smooth` and the `report`.

With the default parameters the core returns 2250 vertices, 2242 faces. The package tests pin these numbers.

## Limits

Ends are closed but not ground flat, so the spring does not stand on a flat face. The height changes pitch abruptly where active coils meet end coils. The rate uses the basic formula G d^4 / (8 D^3 n) without the Wahl curvature correction and assumes small deflections. Extension spring hooks are not modelled. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Helix sweep in the radial and tangent frame without twist
- Piecewise pitch for closed end coils
- Helical spring rate k = G d^4 / (8 D^3 n)

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
