# Involute spur gear

Builds a spur gear whose tooth flanks are involutes of the base circle, so two gears with the same module and pressure angle mesh with a constant speed ratio. The outline is computed point by point from the involute function, offset so each tooth is half the circular pitch thick on the pitch circle minus the backlash, then extruded to the face width. The caps are triangulated to the bore circle; a solid gear gets one polygon per cap.

## When to use it

Use it for clocks, gearboxes, mechanical props and animated gear trains where teeth must visibly mesh. Two gears mesh when their modules and pressure angles match and their centres are the sum of their pitch radii apart.

## Use it

### As an add-on

1. In Blender 4.2 or newer, open Edit > Preferences > Add-ons, choose Install from Disk and select `spur_gear_involute.py`.
2. Enable "Baltor Involute Spur Gear".
3. Run it from View3D > Add > Mesh > Involute Spur Gear. The operator is `baltor.spur_gear_involute`; its redo panel shows every parameter listed below.

### As a script

```
blender --background --python spur_gear_involute.py -- --teeth 32 --module 0.002 --face_width 0.01 --bore_diameter 0.008 --output result.blend
```

Every parameter is written `--name value`. Vectors are written `x,y,z` and booleans `true` or `false`. `--output` saves a `.blend` file, or a glTF file when the name ends in `.glb` or `.gltf`.

### From Python

The core needs no Blender:

```python
import spur_gear_involute
gear = spur_gear_involute.build_geometry(teeth=32, module=0.002)
print(gear["report"]["pitch_diameter_m"])  # 0.064
print(spur_gear_involute.involute(0.349066))  # inv(20 degrees) = 0.0149
```

Inside Blender, `spur_gear_involute.create(bpy.context, ...)` takes the same keyword parameters and builds the result in the open file.

## Parameters

| Name | Type | Default | Range | Unit | Meaning |
|---|---|---|---|---|---|
| `teeth` | int | 18 | 6 to 300 | count | Number of teeth. |
| `module` | float | 0.01 | 0.0002 to 1.0 | m | Module: pitch diameter divided by teeth (0.01 m is a module 10 gear). |
| `pressure_angle` | float | 20.0 | 10.0 to 35.0 | degree | Pressure angle of the involute. |
| `face_width` | float | 0.04 | 0.0005 to 5.0 | m | Thickness of the gear along Z. |
| `bore_diameter` | float | 0.03 | 0.0 to 10.0 | m | Diameter of the central hole; 0 for a solid gear. |
| `backlash` | float | 0.0002 | 0.0 to 0.05 | m | Tooth thickness removed on the pitch circle, measured along the arc. |
| `flank_samples` | int | 6 | 2 to 40 | count | Points along each involute flank. |
| `smooth_bore_sides` | int | 32 | 8 to 256 | count | Segments of the bore circle. |

## Outputs

One mesh object named `Spur Gear` with the material `Baltor Gear Steel`, axis along Z, centred on its origin at the 3D cursor. The core returns `vertices`, `faces` and a `report` with the pitch, tip, root and base diameters and the circular pitch, all in metres.

With the default parameters the core returns 640 vertices, 960 faces. The package tests pin these numbers.

## Limits

Standard full-depth teeth only (addendum one module, dedendum 1.25 modules); no profile shift, no undercut or trochoid root fillet, so gears below about 17 teeth at 20 degrees are not exact near the root. The root between teeth is a straight chord, not an arc. No helix, hub or keyway. Fine for rendering and animation; check tolerances before manufacturing. Verified in Blender 5.2.1; written for the 4.2 API.

## Technique

- Involute of a circle and the involute function inv(a) = tan(a) - a
- Tooth thickness of half the circular pitch on the pitch circle
- Annulus triangulation by merging two angle-sorted loops

## Checks

The package tests run the core without Blender and refuse known-wrong inputs. The native check installs the add-on in Blender 5.2.1, runs the operator and the script mode, compares the result with the core, and reopens the saved file in a new Blender process. It also exports glTF and checks the file.
