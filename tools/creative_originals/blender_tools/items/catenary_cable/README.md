# Catenary cable between two points

Builds a cable that hangs between two anchors the way a real chain or wire does: a catenary, not a parabola. Given the slack (cable length over straight distance), the core solves the catenary parameter by bisection, places the curve through both anchors, samples it and sweeps a round section along it with capped ends. The report gives the parameter a, the length, the sag below the chord, the lowest point and how much the anchor tension exceeds the horizontal tension.

## When to use it

Use it for power and telephone lines, cables between poles or buildings, hanging ropes, hoses and festoon lights, where the sag must look physically right for its length.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `catenary_cable.py`.
2. Enable "Baltor Catenary Cable".
3. Run it from View3D > Add > Mesh > Catenary Cable. The operator is `baltor.catenary_cable`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python catenary_cable.py -- --start 0,0,4 --end 8,0,3 --slack 1.04 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import catenary_cable
points, numbers = catenary_cable.curve(start=[0, 0, 4], end=[8, 0, 3], slack=1.04)
print(numbers["sag_below_chord_m"], len(points))
```

Inside Blender, `catenary_cable.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `start` | vector | 0.0,0.0,3.0 | -100000.0 to 100000.0 | m | First anchor point. |
| `end` | vector | 6.0,1.5,2.4 | -100000.0 to 100000.0 | m | Second anchor point; must differ horizontally from start. |
| `slack` | float | 1.05 | 1.0001 to 5.0 | ratio | Cable length divided by the straight distance between the anchors. |
| `radius` | float | 0.015 | 0.0005 to 2.0 | m | Radius of the cable. |
| `segments` | int | 48 | 4 to 1000 | count | Segments along the cable. |
| `sides` | int | 8 | 3 to 64 | count | Sides of the cable section. |

## Outputs

One smooth-shaded mesh object named `Catenary Cable` with the material `Baltor Cable Rubber`, placed at the world origin so its vertices sit at the anchor coordinates. The core returns `vertices`, `faces`, `smooth` and a `report` with `parameter_a_m`, `length_m`, `sag_below_chord_m`, `lowest_point_z_m` and `anchor_tension_over_horizontal`.

With the default parameters the core returns 392 vertices, 386 faces. The package tests pin these numbers.

## Limits

A uniform, perfectly flexible and inextensible cable under gravity only: no wind, stiffness, stretch or point loads. The anchors must differ horizontally; a vertical hang is refused. Very large slack values make a deep U that the segment count may sample coarsely. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Catenary y = a cosh((x - x0) / a) + c through two points with a given arc length
- Bisection on the monotone function 2 a sinh(h / (2 a))
- Parallel transport of a section frame along a sampled curve

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
