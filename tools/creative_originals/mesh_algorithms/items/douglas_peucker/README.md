# Ramer-Douglas-Peucker polyline simplification

Reduces the number of points of a polyline while keeping its shape within a tolerance: the end points stay, and recursively the point farthest from the current chord is kept while that distance exceeds the tolerance.

## When to use it

Use it to thin GPS tracks and recorded paths, to lighten contour lines and vector strokes, and to reduce point counts before triangulating or extruding outlines.

## How it works

An explicit stack of index ranges replaces recursion. For each range the point with the largest distance to the chord segment is found; if it exceeds the tolerance it is kept and both halves are pushed. max_deviation measures the largest distance from any original point to the result.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `tolerance` | float | m | `0.05` | 0 to 1e+06 | Largest allowed distance from a removed point to the simplified polyline. |
| `samples` | int | count | `400` | 2 to 1000000 | Points in the demonstration curve before simplification. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 douglas_peucker.py --output model.gltf --tolerance 0.05 --samples 400
```

From Python:

```python
from douglas_peucker import simplify, max_deviation

track = [(x * 0.1, (x * 0.1) ** 2 % 1.0) for x in range(200)]
short = simplify(track, tolerance=0.02)
print(len(short), max_deviation(track, short))
```

Entry points:

- `simplify(points, tolerance=0.05)`: The kept points, in order: both ends, and recursively the point farthest from the current chord segment while that distance exceeds ``tolerance``. Iterative (no recursion limit). O(n log n) typical, O(n^2) worst.
- `max_deviation(original, simplified)`: Largest distance from any original point to the simplified polyline (0 when nothing was removed).
- `demo_curve(samples=400)`: A 3D test curve: a spiral with a superimposed wobble.
- `build(tolerance=0.05, samples=400)`: Two tubes: the original curve (thin, grey) and its simplification (thicker, coloured).
- `main(argv=None)`: Command line: write both tubes (.gltf or .obj) and print a JSON summary.

## Complexity

O(n log n) typical, O(n^2) worst case.

## Outputs

- `.gltf`: two tubes: the original curve (thin, grey) and the simplified one (thicker)
- `.obj`: the same tubes as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `collinear`: `simplify(points=[10 items], tolerance=0)` gives points matching the listed coordinates.
- `deviation_bound`: `max_deviation(original=demo_curve(...), simplified=simplify(...))` gives at most 0.05.
- `display`: `build()` gives 2 meshes; watertight.
- `reference_example`: `simplify(points=[10 items], tolerance=1)` gives points matching the listed coordinates.
- `zero_tolerance_keeps_corners`: `simplify(points=demo_curve(...), tolerance=0)` gives 400 points.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Distances are measured to chord segments, and the result keeps the original end points. The simplified line can cross itself or other lines (no topology preservation). Not suited to closed rings without choosing a split point first.
