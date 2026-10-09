# B-spline curves with de Boor evaluation and knot insertion

Evaluates B-spline curves of any degree with de Boor's triangular scheme. Clamped curves start and end on their first and last control points; periodic curves loop through the wrapped control polygon. Basis functions and Boehm knot insertion are included.

## When to use it

Use it for smooth camera and object paths, animation curves, CAD-style curve editing (insert a knot before moving a local control point) and as the basis of surface patches.

## How it works

The knot span holding t is found by binary search; de Boor then blends degree + 1 control points level by level with weights (t - k_left) / (k_right - k_left). Basis values use the triangular Cox-de Boor table. Knot insertion replaces degree control points with blends of neighbours so the curve is unchanged.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `degree` | int | degree | `3` | 1 to 7 | Polynomial degree of the curve. |
| `closed` | bool | flag | `False` | any to any | Periodic curve through the control polygon's loop instead of a clamped open curve. |
| `samples` | int | count | `160` | 2 to 100000 | Points sampled along the curve for the display tube. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 bspline_de_boor.py --output model.gltf --degree 3 --closed False --samples 160
```

From Python:

```python
from bspline_de_boor import sample_curve, clamped_knots, insert_knot

points = sample_curve([(0, 0, 0), (1, 2, 0), (3, 2, 1), (4, 0, 0)], degree=3, samples=100)
```

Entry points:

- `clamped_knots(count, degree)`: Clamped uniform knot vector in [0, 1] for ``count`` control points: degree + 1 repeated end knots.
- `de_boor(controls, degree, knots, t)`: Curve point at t by de Boor's triangular scheme (the stable form of the B-spline sum).
- `basis_functions(degree, knots, count, t)`: All ``count`` basis function values N_i,degree(t) by the Cox-de Boor recursion; they sum to 1 on the domain.
- `insert_knot(controls, degree, knots, t)`: Boehm knot insertion: (new controls, new knots) describing the same curve with one more control point.
- `sample_curve(controls, degree=3, samples=160, closed=False)`: ``samples`` points along a clamped curve (ends on the first and last control points) or, when closed, a uniform periodic curve through the wrapped control loop (no repeated end point).
- `build(degree=3, closed=False, samples=160)`: A tube along the demonstration curve plus line segments of its control polygon.
- `main(argv=None)`: Command line: write the curve tube and control polygon (.gltf or .obj) and print a JSON summary.

## Complexity

O(degree^2) per point.

## Outputs

- `.gltf`: a tube along the curve plus a LINES primitive for the control polygon
- `.obj`: the same tube and polygon lines as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `basis_values`: `basis_functions(degree=3, knots=[11 items], count=7, t=0.37)` gives values matching the listed numbers (tolerance 1e-14).
- `clamped_ends`: `sample_curve(controls=[7 items], degree=3, samples=50)` gives 50 points; first point [-2.0, 0.0, 0.0]; last point [2.4, 0.0, -0.8].
- `clamped_knot_vector`: `clamped_knots(count=7, degree=3)` gives exactly [11 items].
- `degree_one_is_polyline`: `sample_curve(controls=[3 items], degree=1, samples=5)` gives points matching the listed coordinates.
- `display`: `build()` gives watertight; 6 line segments.
- `knot_insertion`: `insert_knot(controls=[7 items], degree=3, knots=[11 items], t=0.3)` (selecting `0`) gives 8 entries; values matching the listed numbers (tolerance 1e-14).
- `periodic_loop`: `sample_curve(controls=[7 items], degree=3, samples=40, closed=True)` gives 40 points.
- `quadratic_is_bezier`: `de_boor(controls=[3 items], degree=2, knots=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0], t=0.5)` gives values matching the listed numbers (tolerance 1e-15).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Non-rational only (see nurbs_curve for weights). Knot vectors must be non-decreasing with the usual multiplicity limits; clamped_knots builds uniform interior knots only. The control polygon in the display mesh is a LINES primitive, which draws one pixel wide in most viewers.
