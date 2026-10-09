# 2D Delaunay triangulation by Bowyer-Watson

Computes the Delaunay triangulation of a 2D point set. The result lists counter-clockwise triangles as index triples into the input points and the counter-clockwise hull loop.

## When to use it

Use it to mesh scattered terrain samples, to interpolate values over irregular points, to build a Voronoi diagram from the dual, or to make a well shaped triangle mesh from a point set.

## How it works

A large super-triangle encloses the points. Each point is inserted by removing every triangle whose circumcircle strictly contains it and joining the cavity boundary to the point. The orientation and in-circle determinants are evaluated in floating point and, when the result is within a conservative error bound, again with exact fractions. Triangles touching the super-triangle are removed, any concave notch on the boundary is filled, and Lawson flips make every interior edge locally Delaunay.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `count` | int | count | `160` | 3 to 20000 | Number of input points. |
| `layout` | str | name | `random` | one of `random`, `jittered_grid`, `rings` | How the demonstration points are placed in the unit square. |
| `seed` | int | integer | `11` | 0 to 2147483647 | Random seed; the same seed gives the same points. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 delaunay_bowyer_watson.py --output model.gltf --count 160 --layout random --seed 11
```

From Python:

```python
from delaunay_bowyer_watson import delaunay

result = delaunay([(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.4)])
print(result["triangles"], result["hull"])
```

Entry points:

- `delaunay(points)`: Delaunay triangulation of 2D points: {"points", "triangles", "hull"}.
- `random_points(count=160, layout='random', seed=11)`: Seeded demonstration points in the unit square: uniform 'random', 'jittered_grid' or concentric 'rings'.
- `triangulation_mesh(result, height=0.0)`: A flat glTF-ready mesh of a triangulation: one colour per triangle, the plane facing +Y.
- `build(count=160, layout='random', seed=11)`: The coloured triangulation of seeded points that the command line writes.
- `main(argv=None)`: Command line: write the triangulation as .gltf or .obj and print a JSON summary.

## Complexity

O(n^2). Each insertion tests every current triangle; the final Lawson pass is usually near linear.

## Outputs

- `.gltf`: the triangulation of seeded points as a flat mesh in the XZ plane, one colour per triangle (COLOR_0)
- `.obj`: the same flat mesh as Wavefront OBJ

Axes and units: +Y up, metres; 2D (x, y) maps to (x, 0, -y).

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `cocircular_grid`: `delaunay(points=[16 items])` gives 18 triangles; empty circumcircles (Delaunay); every triangle counter-clockwise; every input point used; triangle areas summing to 9 (tolerance 1e-12).
- `duplicate_point`: `delaunay(points=[5 items])` gives 2 triangles; not every point used; empty circumcircles (Delaunay); triangle areas summing to 1.1 (tolerance 1e-12).
- `hexagon_and_centre`: `delaunay(points=[7 items])` gives 6 triangles; empty circumcircles (Delaunay); every triangle counter-clockwise; every input point used; triangle areas summing to 2.59808 (tolerance 1e-12).
- `random_points`: `delaunay(points=random_points(...))` gives 226 triangles; empty circumcircles (Delaunay); every triangle counter-clockwise; every input point used; triangle areas summing to 0.89003 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Quadratic insertion: suited to thousands of points, not millions. Exact rational arithmetic is used only when the floating-point predicate is too close to call, which is slow for large degenerate inputs. Exact duplicate points are used once. Collinear input raises an error. No constraint edges; see a constrained triangulation for polygons with holes.
