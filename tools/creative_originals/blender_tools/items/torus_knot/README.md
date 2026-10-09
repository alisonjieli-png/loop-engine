# Torus knot tube without a twist seam

Builds a tube along a (p, q) torus knot: the curve winds p times around the Z axis and q times through the hole of a torus. The round section is carried along the curve by parallel transport, which avoids the sudden flips of Frenet frames. After one loop the transported frame comes back rotated about the tangent; that angle is removed in equal steps along the loop, so the last ring meets the first without a twist seam. The result is one closed, smooth-shaded surface.

## When to use it

Use it for pendants, rings, logos, abstract sculptures, motion graphics and maths teaching. (2, 3) is the trefoil, (2, 5) the cinquefoil, and (3, 4) or (3, 5) give denser knots.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `torus_knot.py`.
2. Enable "Baltor Torus Knot".
3. Run it from View3D > Add > Mesh > Torus Knot. The operator is `baltor.torus_knot`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python torus_knot.py -- --p 3 --q 5 --tube_radius 0.08 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import torus_knot
knot = torus_knot.build_geometry(p=3, q=5)
print(knot["report"]["crossing_number"])  # 10
```

Inside Blender, `torus_knot.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `p` | int | 2 | 1 to 30 | count | Turns around the Z axis. |
| `q` | int | 3 | 1 to 30 | count | Turns through the hole; coprime with p. |
| `major_radius` | float | 1.0 | 0.01 to 1000.0 | m | Radius R of the torus the knot lies on. |
| `minor_radius` | float | 0.42 | 0.001 to 1000.0 | m | Radius a of the torus tube the knot winds around; less than R. |
| `tube_radius` | float | 0.13 | 0.0005 to 100.0 | m | Radius of the swept tube. |
| `samples` | int | 240 | 16 to 4000 | count | Rings along the knot. |
| `sides` | int | 12 | 3 to 64 | count | Sides of the tube section. |

## Outputs

One smooth-shaded mesh object named `Torus Knot` with the material `Baltor Knot`, centred on the 3D cursor. The core returns `vertices`, `faces`, `smooth` and a `report` with the curve length, the transport twist that was removed and the crossing number.

With the default parameters the core returns 2880 vertices, 2880 faces. The package tests pin these numbers.

## Limits

Coprime p and q only, since other pairs give links of several loops. The tube can intersect itself when the tube radius is large compared with the gaps between strands; nothing checks or prevents this. Parallel transport is discrete, so very few samples give a visibly faceted tube. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Torus knot parametrisation ((R + a cos qt) cos pt, (R + a cos qt) sin pt, a sin qt)
- Parallel transport of a normal along a closed curve and its holonomy angle
- Crossing number of a torus knot min(p(q - 1), q(p - 1))

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
