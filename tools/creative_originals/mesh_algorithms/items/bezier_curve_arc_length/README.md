# Cubic Bezier evaluation, arc length and resampling

Works with cubic Bezier curves: points by de Casteljau, velocity, splitting at a parameter, arc length by Gauss-Legendre quadrature, the parameter at a given length, and resampling of a multi-segment path at even arc-length spacing.

## When to use it

Use it to move cameras or objects at constant speed along a path, to place fence posts or particles evenly along a curve, or to measure and split curves from SVG or font outlines.

## How it works

The speed |B'(t)| is integrated with five-point Gauss-Legendre quadrature on equal parameter pieces. A cumulative table of piece lengths turns a target length into a piece, inside which Newton steps solve length(t) = target using the speed as the derivative. Splitting uses the intermediate points of de Casteljau's construction.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `path` | str | name | `wave` | one of `wave`, `loop`, `quarter_circle` | Demonstration path made of cubic segments. |
| `spacing` | float | m | `0.05` | 0.001 to 1000 | Arc-length spacing of the resampled points the tube follows. |
| `tube_radius` | float | m | `0.04` | 0.0001 to 1000 | Radius of the display tube. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 bezier_curve_arc_length.py --output model.gltf --path wave --spacing 0.05 --tube-radius 0.04
```

From Python:

```python
from bezier_curve_arc_length import arc_length, resample_by_length

segment = [(0, 0, 0), (1, 2, 0), (3, 2, 0), (4, 0, 0)]
print(arc_length(segment))
posts = resample_by_length([segment], spacing=0.25)
```

Entry points:

- `bezier_point(controls, t)`: Point at parameter t in [0, 1] by de Casteljau's repeated linear interpolation (any dimension).
- `bezier_derivative(controls, t)`: Velocity dB/dt of a cubic at t: 3 [(1-t)^2 (P1-P0) + 2 (1-t) t (P2-P1) + t^2 (P3-P2)].
- `split_bezier(controls, t=0.5)`: The two cubics that trace the parts before and after t (de Casteljau's intermediate points).
- `arc_length(controls, t0=0.0, t1=1.0, pieces=16)`: Length of a cubic between t0 and t1: five-point Gauss-Legendre quadrature of the speed on ``pieces`` equal sub-intervals (error falls like the tenth power of the piece size for smooth speed).
- `length_table(controls, pieces=32)`: Cumulative arc length at t = k / pieces for k = 0 .. pieces (the lookup table for inversion).
- `parameter_at_length(controls, length, table=None)`: The t whose arc length from 0 equals ``length``: find the table piece, then Newton steps inside it.
- `resample_by_length(segments, spacing)`: Points along a path of cubic segments spaced ``spacing`` apart in arc length, plus the final end point.
- `demo_path(name='wave')`: Cubic segments of a demonstration path: 'wave' (four arches), 'loop' (closed) or 'quarter_circle'.
- `build(path='wave', spacing=0.05, tube_radius=0.04)`: A tube through the path resampled at even arc length (what the command line writes).
- `main(argv=None)`: Command line: write the resampled path as a tube (.gltf or .obj) and print a JSON summary.

## Complexity

O(pieces) per length query; O(points * log pieces) for resampling. The length table holds 32 Gauss-Legendre pieces per segment; inversion is a table search plus Newton steps.

## Outputs

- `.gltf`: a tube along the resampled demonstration path with POSITION and NORMAL
- `.obj`: the same tube as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `display_tube`: `build()` gives watertight; unit vertex normals.
- `even_spacing_on_uneven_speed`: `resample_by_length(segments=[1 items], spacing=0.5)` gives 7 points; points matching the listed coordinates.
- `midpoint`: `bezier_point(controls=[4 items], t=0.5)` gives values matching the listed numbers (tolerance 1e-15).
- `quarter_circle_length`: `arc_length(controls=[4 items])` gives value 1.57102 (tolerance 1e-09).
- `split_first_half`: `split_bezier(controls=[4 items], t=0.5)` (selecting `0`) gives values matching the listed numbers (tolerance 1e-15).
- `start_velocity`: `bezier_derivative(controls=[4 items], t=0)` gives values matching the listed numbers (tolerance 1e-15).
- `straight_line_length`: `arc_length(controls=[4 items])` gives value 3 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Cubic segments only (the evaluation works for any degree, the length and split functions take four control points). Arc length is numerical (five-point Gauss-Legendre on 16 or 32 pieces), accurate to about 1e-10 for smooth segments but slower to converge near cusps. The display tube is for viewing, not a production sweep.
