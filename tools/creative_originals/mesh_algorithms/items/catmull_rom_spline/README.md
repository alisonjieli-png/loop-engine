# Centripetal Catmull-Rom spline

Builds a curve that passes through every control point. Knot spacing |p_(i+1) - p_i|^alpha with alpha 0 (uniform), 0.5 (centripetal) or 1 (chordal) controls how the curve treats uneven spacing; centripetal spacing avoids cusps and self-intersections inside a segment.

## When to use it

Use it for paths through waypoints: camera rails, patrol routes, race tracks, roads and rivers drawn from clicked points, and smooth interpolation of keyed positions.

## How it works

Each segment between p1 and p2 uses neighbours p0 and p3. Knots t0..t3 accumulate the spaced distances, and the point at parameter t is found by three levels of linear interpolation (Barry and Goldman's pyramid), which equals the Catmull-Rom cubic for every alpha.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `alpha` | float | exponent | `0.5` | 0 to 1 | Knot spacing exponent: 0 uniform, 0.5 centripetal (no cusps or self-loops), 1 chordal. |
| `closed` | bool | flag | `True` | any to any | Join the last control point back to the first. |
| `samples_per_segment` | int | count | `16` | 1 to 10000 | Points per segment between consecutive control points. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 catmull_rom_spline.py --output model.gltf --alpha 0.5 --closed True --samples-per-segment 16
```

From Python:

```python
from catmull_rom_spline import catmull_rom

rail = catmull_rom([(0, 0, 0), (2, 1, -1), (4, 0, 1), (6, 2, 0)], alpha=0.5, samples_per_segment=24)
```

Entry points:

- `catmull_rom_point(p0, p1, p2, p3, t, alpha=0.5)`: Point between p1 (t = 0) and p2 (t = 1) of the Catmull-Rom segment with knot spacing |dp|^alpha, by the Barry-Goldman pyramid of linear interpolations.
- `catmull_rom(points, alpha=0.5, closed=False, samples_per_segment=16)`: Points of the spline through every control point; each segment contributes ``samples_per_segment`` points starting at its first control point, and an open spline ends exactly on the last point. Open ends use a reflected neighbour (2 p0 - p1) so the end tangents follow the first and last segments.
- `build(alpha=0.5, closed=True, samples_per_segment=16)`: A tube through the demonstration control points plus small markers at each control point.
- `main(argv=None)`: Command line: write the spline tube and control markers (.gltf or .obj) and print a JSON summary.

## Complexity

O(points * samples_per_segment).

## Outputs

- `.gltf`: a tube along the spline and a mesh of small control-point markers
- `.obj`: the same meshes as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `centripetal_matches_tangent_form`: `catmull_rom_point(p0=[0.0, 0.0, 0.0], p1=[1.0, 0.2, 0.0], p2=[1.7, 1.4, 0.3], p3=[0.4, 2.0, -0.5], t=0.6, alpha=0.5)` gives values matching the listed numbers (tolerance 1e-14).
- `closed_loop`: `catmull_rom(points=[4 items], closed=True, samples_per_segment=8)` gives 32 points; first point [1.0, 0.0, 0.0].
- `display`: `build()` gives 2 meshes; watertight.
- `even_line`: `catmull_rom(points=[4 items], alpha=0, closed=False, samples_per_segment=4)` gives 13 points; points matching the listed coordinates.
- `passes_through_end`: `catmull_rom_point(p0=[0.0, 0.0, 0.0], p1=[1.0, 0.2, 0.0], p2=[1.7, 1.4, 0.3], p3=[0.4, 2.0, -0.5], t=1)` gives values matching the listed numbers (tolerance 0).
- `passes_through_start`: `catmull_rom_point(p0=[0.0, 0.0, 0.0], p1=[1.0, 0.2, 0.0], p2=[1.7, 1.4, 0.3], p3=[0.4, 2.0, -0.5], t=0)` gives values matching the listed numbers (tolerance 0).
- `uniform_matches_matrix_form`: `catmull_rom_point(p0=[0.0, 0.0, 0.0], p1=[1.0, 0.2, 0.0], p2=[1.7, 1.4, 0.3], p3=[0.4, 2.0, -0.5], t=0.3, alpha=0)` gives values matching the listed numbers (tolerance 1e-14).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Interpolating splines have only C1 continuity at the control points (curvature may jump). Coincident consecutive control points are separated by a tiny knot gap. Open ends use reflected neighbour points, one of several conventions.
