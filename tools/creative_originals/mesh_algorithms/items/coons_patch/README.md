# Coons patch from four boundary curves

Builds the surface spanning four boundary curves as the sum of two ruled surfaces minus the bilinear surface through the corners. Every boundary vertex lies exactly on its curve.

## When to use it

Use it to fill holes bounded by four edges, to make cloth and sail panels, road and terrain fills between known edges, car body patches, or quick surfaces from sketched outlines.

## How it works

S(u, v) = (1 - v) bottom(u) + v top(u) + (1 - u) left(v) + u right(v) minus the bilinear blend of the four corners. The grid samples u and v evenly; normals are angle weighted from the faces.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `boundary` | str | name | `saddle` | one of `saddle`, `pillow`, `flat` | Demonstration set of four boundary curves. |
| `resolution` | int | cells | `24` | 1 to 4096 | Grid cells per side; the patch has (resolution + 1)^2 vertices. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 coons_patch.py --output model.gltf --boundary saddle --resolution 24
```

From Python:

```python
from coons_patch import coons_patch

patch = coons_patch([[(0, 0, 0), (1, 0.4, 0), (2, 0, 0)], [(0, 0, -2), (2, 0, -2)],
                     [(0, 0, 0), (0, 0, -2)], [(2, 0, 0), (2, 0, -2)]], resolution=16)
```

Entry points:

- `coons_point(bottom, top, left, right, u, v)`: S(u, v) = ruled(u) + ruled(v) - bilinear corners, for boundary functions of one parameter in [0, 1]: bottom(u) = S(u, 0), top(u) = S(u, 1), left(v) = S(0, v), right(v) = S(1, v); the corners must agree.
- `polyline_function(points)`: A boundary function t -> point that follows a polyline by arc length (t = 0 first point, 1 last).
- `demo_boundary(name='saddle')`: (bottom, top, left, right) boundary functions over a 2 x 2 square in XZ.
- `coons_patch(boundary, resolution=24)`: A (resolution + 1)^2 grid mesh of the Coons patch with normals from the mesh; boundary vertices lie exactly on the boundary curves. ``boundary`` is (bottom, top, left, right), each a function of one parameter in [0, 1] or a polyline (followed by arc length). Faces wind so the normal follows (dS/dv) x (dS/du), which points +Y for the demonstration squares.
- `build(boundary='saddle', resolution=24)`: The demonstration patch, coloured by height.
- `main(argv=None)`: Command line: write the patch (.gltf or .obj) and print a JSON summary.

## Complexity

O(resolution^2).

## Outputs

- `.gltf`: the patch with POSITION, NORMAL and COLOR_0 by height, double-sided
- `.obj`: the same patch as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `flat_square`: `coons_patch(boundary=demo_boundary(...), resolution=4)` gives 25 vertices; 16 faces; surface area 4 (tolerance 1e-12); every vertex on the plane n . p = 0, n = [0.0, 1.0, 0.0]; 1 boundary loops.
- `polyline_boundary`: `coons_patch(boundary=[4 items], resolution=4)` gives 25 vertices; 16 faces; bounds [0.0, 0.0, -2.0] to [2.0, 0.5, 0.0].
- `saddle_bounds`: `coons_patch(boundary=demo_boundary(...), resolution=8)` gives 81 vertices; 64 faces; bounds [-1.0, -0.5, -1.0] to [1.0, 0.5, 1.0].
- `saddle_centre`: `coons_point(bottom=demo_boundary(...), top=demo_boundary(...), left=demo_boundary(...), right=demo_boundary(...), u=0.5, v=0.5)` gives values matching the listed numbers (tolerance 1e-15).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The four curves must meet at their corners (not checked). Bilinear blending matches positions only (C0 across patch borders), not tangents. Polyline boundaries are followed by arc length, so their corners do not line up with grid lines in general.
