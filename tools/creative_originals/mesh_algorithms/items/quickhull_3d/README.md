# 3D convex hull by quickhull

Computes the convex hull of a 3D point set with quickhull. The result is a closed mesh whose faces point outward; coplanar neighbouring triangles merge into one convex polygon, so the hull of a cube's corners is six quads.

## When to use it

Use it to build convex collision shapes from render meshes, to bound a point cloud, to test whether points are inside a convex region, or to make faceted crystal and gem shapes from random points.

## How it works

The extreme points along the axes give the longest starting edge; the point farthest from that line and the point farthest from the resulting plane complete a tetrahedron. Every other point is assigned to one face it lies outside of. Repeatedly the farthest point of a face is taken, the faces it can see are found by a walk across neighbours, their horizon edges are joined to the point, and the orphaned points are reassigned to the new faces. Finally faces whose planes agree are merged with a union-find over shared edges and each group's boundary becomes one polygon.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `count` | int | count | `300` | 4 to 100000 | Number of random input points. |
| `distribution` | str | name | `ball` | one of `ball`, `cube`, `sphere`, `gaussian` | Where the random points are drawn. |
| `seed` | int | integer | `5` | 0 to 2147483647 | Random seed; the same seed gives the same points. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 quickhull_3d.py --output model.gltf --count 300 --distribution ball --seed 5
```

From Python:

```python
from quickhull_3d import convex_hull, random_points

hull = convex_hull(random_points(500, "ball", seed=1))
print(len(hull.vertices), len(hull.faces))
```

Entry points:

- `convex_hull(points, merge_coplanar=True, tolerance=None)`: The convex hull of 3D points as a closed mesh with outward faces.
- `sphere_points(count=60, radius=1.0)`: ``count`` points spread evenly on a sphere by the golden-angle (Fibonacci) spiral; every point is extreme.
- `random_points(count=300, distribution='ball', seed=5)`: Seeded random points in the unit ball, the cube [-1, 1]^3, on the unit sphere, or Gaussian (sigma 0.5).
- `build(count=300, distribution='ball', seed=5)`: The faceted hull of seeded random points that the command line writes.
- `main(argv=None)`: Command line: write the hull of random points as .gltf or .obj and print a JSON summary.

## Complexity

O(n log n) expected, O(n^2) worst case. Each point is tested against the faces that may see it; the merge step is linear in the hull size.

## Outputs

- `.gltf`: the hull of seeded random points, flat shaded (each face owns its corners)
- `.obj`: the same faceted hull as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `cube_with_interior_points`: `convex_hull(points=[14 items])` gives 8 vertices; 6 faces; 12 triangles; volume 1 (tolerance 1e-12); surface area 6 (tolerance 1e-12); watertight; convex; Euler characteristic 2; contains every input point.
- `fibonacci_sphere`: `convex_hull(points=sphere_points(...))` gives 60 vertices; 116 faces; 116 triangles; watertight; Euler characteristic 2; convex; every vertex at distance 1 from [0.0, 0.0, 0.0].
- `lattice_with_coplanar_points`: `convex_hull(points=[64 items])` gives 8 vertices; 6 faces; volume 27 (tolerance 1e-09); watertight; convex; bounds [0.0, 0.0, 0.0] to [3.0, 3.0, 3.0].
- `octahedron`: `convex_hull(points=[7 items])` gives 6 vertices; 8 faces; volume 1.33333 (tolerance 1e-12); surface area 6.9282 (tolerance 1e-12); watertight; convex.
- `random_ball`: `convex_hull(points=random_points(...), merge_coplanar=False)` gives watertight; convex; Euler characteristic 2; contains every input point; inside [-1.0, -1.0, -1.0] to [1.0, 1.0, 1.0].

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Floating-point predicates with a relative tolerance (1e-9 of the bounding-box diagonal): points closer than that to a face count as inside, and nearly coplanar faces may stay split. Fewer than four distinct points, or points that are all collinear or coplanar, raise an error. The command line output is flat shaded, so it is not closed as stored; the function result is closed.
