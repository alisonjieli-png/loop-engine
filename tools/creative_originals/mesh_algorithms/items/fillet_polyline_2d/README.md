# Fillet polygon corners with arcs

Replaces every corner of a polygon (or the inner corners of a polyline) by a circular arc of the given radius that touches both edges. For a square of side a and radius r with k chords per arc the area is exactly (a - 2r)^2 + 4(a - 2r)r + 2k r^2 sin(pi / 2k).

## When to use it

Use it for rounded rectangles and badges, cutter toolpaths, rounded floor plans and roads, and to soften any polygon before extrusion.

## How it works

At each corner the unit edge directions give the interior angle. The tangent points sit r / tan(angle / 2) along each edge (limited to half the edge, which shrinks r), the centre lies on the bisector at r / sin(angle / 2), and the arc is sampled between the tangent points.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `0.3` | 0 to 1e+06 | Fillet radius; reduced at a corner whose edges are too short to hold it. |
| `arc_segments` | int | count | `8` | 1 to 4096 | Straight segments per arc. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 fillet_polyline_2d.py --output model.gltf --radius 0.3 --arc-segments 8
```

From Python:

```python
from fillet_polyline_2d import fillet

badge = fillet([(0, 0), (4, 0), (4, 2), (0, 2)], radius=0.5, arc_segments=12)
```

Entry points:

- `fillet(points, radius=0.3, arc_segments=8, closed=True)`: Points of the polygon (or open polyline) with each corner replaced by ``arc_segments`` + 1 points of an arc of ``radius`` tangent to both edges. The tangent points sit radius / tan(angle / 2) from the corner, limited to half of each edge (the radius shrinks to fit). Straight corners are kept as they are.
- `perimeter(points, closed=True)`: Length of the polygon (or polyline).
- `build(radius=0.3, arc_segments=8)`: The filleted demonstration outline as a flat plate in the XZ plane facing +Y.
- `main(argv=None)`: Command line: write the filleted outline (.gltf or .obj) and print a JSON summary.

## Complexity

O(n * arc_segments).

## Outputs

- `.gltf`: the filleted demonstration outline as a flat plate in the XZ plane facing +Y
- `.obj`: the same plate as Wavefront OBJ

Axes and units: +Y up, metres; 2D (x, y) maps to (x, 0, -y).

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `open_polyline_keeps_ends`: `fillet(points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]], radius=0.2, arc_segments=4, closed=False)` gives 7 points; first point [0.0, 0.0]; last point [1.0, 1.0].
- `perimeter`: `perimeter(points=[4 items])` gives value 8 (tolerance 1e-15).
- `radius_shrinks_to_fit`: `fillet(points=[4 items], radius=5, arc_segments=4)` gives 16 points; polygon area 3.06147 (tolerance 1e-12); every point at distance 1 from [0.0, 0.0].
- `square`: `fillet(points=[4 items], radius=0.5, arc_segments=8)` gives 36 points; polygon area 3.78036 (tolerance 1e-12); closed polyline length 7.13655 (tolerance 1e-12); simple polygons.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Each corner is filleted on its own: where a shrunk radius takes half of an edge from both ends, the arcs meet but the radius is no longer the requested one. Self-intersecting input is not repaired. Arcs are polylines with arc_segments chords.
