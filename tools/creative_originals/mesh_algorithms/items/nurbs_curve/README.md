# NURBS curves with exact circles and conics

Evaluates NURBS curves by running de Boor's algorithm on weighted homogeneous points and dividing by the weight. The nine-point circle is exact to rounding, and one rational quadratic span gives an ellipse, parabola or hyperbola arc depending on its middle weight.

## When to use it

Use it where circles and conic arcs must be exact: CAD and CAM data, gear and cam profiles, architectural arcs, or round paths that must not drift from their radius.

## How it works

Each control point P with weight w becomes (w P, w). De Boor blends these four-dimensional points and the result is divided by its last coordinate. The circle uses the corners and edge midpoints of a square with corner weights sqrt(2) / 2 and doubled interior knots at quarters.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `1.0` | 1e-06 to 1e+06 | Radius of the exact NURBS circle that the command line draws. |
| `samples` | int | count | `48` | 3 to 100000 | Points sampled along each curve for the display tubes. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 nurbs_curve.py --output model.gltf --radius 1.0 --samples 48
```

From Python:

```python
from nurbs_curve import circle, sample_nurbs

ring = sample_nurbs(circle(radius=0.5), samples=64, closed=True)
```

Entry points:

- `nurbs_point(controls, weights, degree, knots, t)`: Point of the rational B-spline at t: de Boor on (w x, w y, w z, w), then divide by w.
- `circle(radius=1.0, center=(0.0, 0.0, 0.0))`: The exact circle in the XZ plane as a degree-2 NURBS: nine control points on a square (corner weights sqrt(2) / 2) and knots 0 0 0 1/4 1/4 1/2 1/2 3/4 3/4 1 1 1. Returns (controls, weights, degree, knots).
- `conic_arc(start, control, end, weight)`: A single rational quadratic arc: weight < 1 ellipse, 1 parabola, > 1 hyperbola, through start and end with tangents toward ``control``. Returns (controls, weights, degree, knots).
- `sample_nurbs(curve, samples=128, closed=False)`: ``samples`` points evenly spaced in the parameter (the last one left out for a closed curve).
- `build(radius=1.0, samples=48)`: Tubes along the exact circle and three conic arcs (ellipse, parabola, hyperbola) beside it.
- `main(argv=None)`: Command line: write the circle and conic tubes (.gltf or .obj) and print a JSON summary.

## Complexity

O(degree^2) per point.

## Outputs

- `.gltf`: tubes along the exact circle and three conic arcs (ellipse, parabola, hyperbola)
- `.obj`: the same tubes as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `circle_at_one_eighth`: `nurbs_point(controls=circle(...), weights=circle(...), degree=2, knots=[12 items], t=0.125)` gives values matching the listed numbers (tolerance 1e-15).
- `display`: `build()` gives 4 meshes; watertight.
- `exact_circle`: `sample_nurbs(curve=circle(...), samples=100, closed=True)` gives 100 points; every point at distance 2 from [0.0, 0.0, 0.0].
- `parabola_conic`: `sample_nurbs(curve=conic_arc(...), samples=3)` gives points matching the listed coordinates.
- `quarter_circle_conic`: `sample_nurbs(curve=conic_arc(...), samples=9)` gives every point at distance 1 from [0.0, 0.0, 0.0]; 9 points.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The parameter is not proportional to arc length (points crowd toward the square's edge midpoints). Weights must be positive. Only curves; see nurbs_surface for surfaces.
