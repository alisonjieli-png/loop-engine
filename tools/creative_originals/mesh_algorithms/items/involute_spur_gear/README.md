# Involute spur gear

Builds a spur gear from its standard dimensions: pitch radius z m / 2, base radius times the cosine of the pressure angle, addendum one module above and root 1.25 modules below the pitch circle. Two gears with the same module and pressure angle mesh at the sum of their pitch radii.

## When to use it

Use it for clockwork, gear trains, machines and mechanical props, or to produce 3D-printable test gears. Place a second gear at distance m (z1 + z2) / 2 and rotate it by half a tooth to mesh.

## How it works

At radius r the flank sits at polar angle pi / (2z) + inv(alpha) - inv(acos(rb / r)) from the tooth centre, which gives half the circular pitch of tooth thickness on the pitch circle. Each tooth is traced counter-clockwise: a radial segment from the root to the base circle, the right involute flank sampled evenly in its roll angle, the tip arc, the left flank and the root arc to the next tooth. The outline and the bore polygon are triangulated for the two caps and joined by quad walls.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `teeth` | int | count | `18` | 6 to 400 | Number of teeth. |
| `module` | float | m | `0.1` | 1e-05 to 1000 | Pitch diameter divided by the tooth count; meshing gears share it. |
| `pressure_angle` | float | degrees | `20.0` | 10 to 35 | Angle between the line of action and the pitch circle tangent. |
| `thickness` | float | m | `0.25` | 1e-06 to 1e+06 | Face width along Y. |
| `bore_radius` | float | m | `0.18` | 0 to 1e+06 | Radius of the centre hole; 0 for none. Must stay inside the root circle. |
| `flank_samples` | int | count | `6` | 1 to 200 | Segments along each involute flank. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 involute_spur_gear.py --output model.gltf --teeth 18 --module 0.1 --pressure-angle 20.0 --thickness 0.25 --bore-radius 0.18 --flank-samples 6
```

From Python:

```python
from involute_spur_gear import spur_gear, gear_radii

pinion = spur_gear(teeth=12, module=0.1)
wheel = spur_gear(teeth=30, module=0.1)
print(sum(gear_radii(12)[:1] + gear_radii(30)[:1]))  # centre distance
```

Entry points:

- `involute_function(angle)`: inv(a) = tan(a) - a, the polar angle swept by the involute at pressure angle a.
- `gear_radii(teeth=18, module=0.1, pressure_angle=20.0)`: (pitch, base, addendum, root) radii: z m / 2, pitch cos(alpha), pitch + m, pitch - 1.25 m.
- `gear_profile(teeth=18, module=0.1, pressure_angle=20.0, flank_samples=6, tip_samples=3, root_samples=4)`: The counter-clockwise 2D outline of the gear, tooth 0 centred on +X.
- `spur_gear(teeth=18, module=0.1, pressure_angle=20.0, thickness=0.25, bore_radius=0.18, flank_samples=6)`: The gear extruded along Y and centred at the origin: two capped faces (triangulated around the bore) and quad side walls, closed and outward. With a bore the solid has genus 1.
- `build(teeth=18, module=0.1, pressure_angle=20.0, thickness=0.25, bore_radius=0.18, flank_samples=6)`: The gear the command line writes: each cap shares its vertices under one flat normal and every wall quad owns its corners, so edges between caps and walls and between flank segments stay crisp.
- `main(argv=None)`: Command line: write the gear as .gltf or .obj and print a JSON summary.

## Complexity

O(teeth * flank_samples).

## Outputs

- `.gltf`: the gear with POSITION and NORMAL: caps share vertices under one normal, wall quads own their corners
- `.obj`: the same gear as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `default`: `spur_gear()` gives 868 vertices; watertight; Euler characteristic 0; genus 1; volume 0.593428 (tolerance 0.00296714); inside [-1.0, -0.125, -1.0] to [1.0, 0.125, 1.0].
- `involute`: `involute_function(angle=0.349066)` gives value 0.0149044 (tolerance 1e-15).
- `no_bore`: `spur_gear(teeth=24, module=0.05, thickness=0.1, bore_radius=0, flank_samples=3)` gives 816 vertices; watertight; Euler characteristic 2; volume 0.110963 (tolerance 0.000665776).
- `outline_point_count`: `gear_profile()` gives 414 entries; simple polygons.
- `radii`: `gear_radii(teeth=18, module=0.1, pressure_angle=20)` gives values matching the listed numbers (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Standard full-depth teeth (addendum 1 module, dedendum 1.25 modules) without profile shift, tip relief or a root fillet: the flank meets the root circle with a radial segment. No backlash is added. Gears with very few teeth undercut in reality; this outline does not model that. The volume check compares with the exact area of the smooth outline within 0.5 percent.
