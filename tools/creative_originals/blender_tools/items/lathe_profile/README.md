# Lathe a profile into a solid or a hollow shell

Revolves a profile, given as radius and height pairs from bottom to top, around the Z axis. Points on the axis become single pole vertices with triangle fans, so the mesh has no zero-area faces. Chaikin corner cutting can round the profile first. With a wall thickness the profile is offset inward and walked back down, which closes an open vase outline into a hollow vessel with a floor and a rim: one closed solid. A sweep below 360 degrees gives a cut away part.

## When to use it

Use it for vases, bottles, cups, bowls, lamp bases, chess pieces, columns and other turned objects, and for quick cut-away views of vessels. Write the profile in metres as the outline of half of the object's cross-section.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `lathe_profile.py`.
2. Enable "Baltor Lathe Profile".
3. Run it from View3D > Add > Mesh > Lathe Profile. The operator is `baltor.lathe_profile`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python lathe_profile.py -- --profile "0,0; 0.2,0; 0.25,0.3; 0.1,0.5" --thickness 0.005 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import lathe_profile
mesh = lathe_profile.build_geometry(profile="0,0; 0.2,0; 0.25,0.3; 0.1,0.5")
print(len(mesh["vertices"]), len(mesh["faces"]))
```

Inside Blender, `lathe_profile.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `profile` | string | `0,0; 0.09,0; 0.12,0.03; 0.15,0.12; 0.155,0.22; 0.12,0.32; 0.07,0.38; 0.06,0.44; 0.075,0.47` | any | m | Profile points as radius,height pairs from bottom to top, separated by semicolons. |
| `segments` | int | 48 | 3 to 512 | count | Segments around the axis. |
| `thickness` | float | 0.006 | 0.0 to 10.0 | m | Wall thickness of a hollow shell; 0 revolves the profile as given. |
| `rounding` | int | 2 | 0 to 5 | count | Chaikin corner-cutting passes applied to the profile first. |
| `angle` | float | 360.0 | 1.0 to 360.0 | degree | Sweep angle; below 360 the cut faces are left open. |
| `smooth` | bool | true | true or false | flag | Shade smooth. |

## Outputs

One mesh object named `Lathe` with a `UVMap` (U around the axis, V along the profile) and the material `Baltor Glazed Ceramic`, axis along Z at the 3D cursor. The core returns `vertices`, `faces`, `uv` and `smooth`.

With the default parameters the core returns 2786 vertices, 2832 faces. The package tests pin these numbers.

## Limits

The shell offset moves each profile point along its averaged normal, so very sharp inner corners or walls thicker than the local curvature allows can fold; such outlines are refused only when the offset crosses the axis. A shell needs a full sweep and an open top. UVs are cylindrical and stretch near the poles. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Surface of revolution with single pole vertices on the axis
- Chaikin corner cutting for open polylines
- Profile offset along averaged vertex normals to build a wall

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
