# Chaikin corner cutting

Cuts every corner of a polygon or polyline: each edge is replaced by its two quarter points. Repeated rounds converge to the uniform quadratic B-spline of the input; for the square of side 2 the area after k rounds is exactly 10/3 + (2/3) / 4^k.

## When to use it

Use it to turn rough polygons into smooth outlines for extrusion, to soften hand-drawn strokes and paths, and for organic 2D shapes such as leaves, blobs and islands.

## How it works

Each round maps every edge (a, b) to (3a + b) / 4 and (a + 3b) / 4. A closed polygon of n points becomes 2n points; an open polyline also keeps its two end points.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `iterations` | int | count | `4` | 0 to 16 | Rounds of corner cutting; each doubles the point count of a closed polygon. |
| `ratio` | float | fraction | `0.25` | 0.01 to 0.49 | Where each edge is cut, as a fraction from each end (0.25 is Chaikin's rule). |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 chaikin_corner_cutting.py --output model.gltf --iterations 4 --ratio 0.25
```

From Python:

```python
from chaikin_corner_cutting import chaikin

blob = chaikin([(0, 0), (2, 0.5), (2.5, 2), (0.5, 2.5)], iterations=5)
```

Entry points:

- `chaikin(points, iterations=1, closed=True, ratio=0.25)`: Each round replaces every edge (a, b) by the points (1 - r) a + r b and r a + (1 - r) b. A closed polygon of n points has n * 2^k points after k rounds; an open polyline keeps both end points and has 2n points after one round. With r = 1/4 the limit is the uniform quadratic B-spline of the input.
- `build(iterations=4, ratio=0.25)`: The rounded demonstration star as a flat plate in the XZ plane, with the input polygon as a thin outline tube.
- `main(argv=None)`: Command line: write the plate and outline (.gltf or .obj) and print a JSON summary.

## Complexity

O(n * 2^iterations).

## Outputs

- `.gltf`: the smoothed demonstration star as a flat plate and the input polygon as a thin tube
- `.obj`: the same meshes as Wavefront OBJ

Axes and units: +Y up, metres; 2D (x, y) maps to (x, 0, -y).

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `converges_to_spline_area`: `chaikin(points=[4 items], iterations=6)` gives 256 points; polygon area 3.3335 (tolerance 1e-12).
- `display`: `build()` gives 2 meshes; 218 faces.
- `one_round`: `chaikin(points=[4 items], iterations=1)` gives 8 points; polygon area 3.5 (tolerance 1e-12); convex polygons.
- `open_keeps_ends`: `chaikin(points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]], iterations=1, closed=False)` gives 6 points; first point [0.0, 0.0]; last point [1.0, 1.0].
- `three_rounds`: `chaikin(points=[4 items], iterations=3)` gives 32 points; polygon area 3.34375 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The curve shrinks inside the control polygon (it approximates, it does not interpolate). Point counts double every round. Ratios other than 1/4 converge to curves that are not the quadratic B-spline.
