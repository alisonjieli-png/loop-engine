# Mitered pipe along a polyline

Builds a pipe with one ring per polyline point. Inner rings lie in the plane bisecting the two segments, found by sliding each cross-section point along its segment direction onto that plane, so neighbouring segments meet without gaps or overlaps.

## When to use it

Use it for ducts, plumbing and conduits, steel frames and railings, neon tubes with straight runs, furniture frames and wiring harnesses that follow straight segments.

## How it works

The cross-section frame is carried from segment to segment by the rotation between their directions. At a corner, a point p + o of the cross-section moves along the segment direction d by -(o . m) / (d . m) to reach the miter plane with normal m (the sum of the two directions). Each cut passes through the centre line, so wedges cancel and the volume is area times length.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `0.12` | 1e-06 to 1e+06 | Circumradius of the regular polygon cross-section. |
| `sides` | int | count | `12` | 3 to 1024 | Sides of the cross-section polygon. |
| `route` | str | name | `plumbing` | one of `plumbing`, `zigzag`, `frame` | Demonstration polyline (frame is closed). |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 mitered_polyline_pipe.py --output model.gltf --radius 0.12 --sides 12 --route plumbing
```

From Python:

```python
from mitered_polyline_pipe import mitered_pipe

duct = mitered_pipe([(0, 0, 0), (2, 0, 0), (2, 1.5, 0), (2, 1.5, -1)], radius=0.2, sides=4)
```

Entry points:

- `mitered_pipe(points, radius=0.12, sides=12, closed=False)`: A pipe with one ring per polyline point: end rings are perpendicular to their segment; every inner ring lies in the bisecting (miter) plane of its two segments, found by projecting the cross-section along the segment direction. The volume equals cross-section area times centre-line length for corners that do not fold back. Open pipes get flat caps; faces point outward.
- `demo_route(name='plumbing')`: Demonstration polylines: a plumbing run with right angles, a zigzag, or a closed rectangular frame.
- `build(radius=0.12, sides=12, route='plumbing')`: The flat-shaded demonstration pipe.
- `main(argv=None)`: Command line: write the pipe (.gltf or .obj) and print a JSON summary.

## Complexity

O(points * sides).

## Outputs

- `.gltf`: the flat-shaded demonstration pipe with POSITION and NORMAL
- `.obj`: the same pipe as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `closed_frame`: `mitered_pipe(points=[4 items], radius=0.1, sides=6, closed=True)` gives 24 vertices; watertight; genus 1; volume 0.166277 (tolerance 1e-12).
- `plumbing`: `mitered_pipe(points=[6 items], radius=0.12, sides=12)` gives watertight; volume 0.2376 (tolerance 1e-12).
- `right_angle`: `mitered_pipe(points=[3 items], radius=0.5, sides=4)` gives 12 vertices; 10 faces; watertight; volume 2.5 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Sharp corners (turning more than about 120 degrees) make long miter spikes; corners closer than the radius overlap. Use profile_sweep or a tube for smooth bends. The cross-section is a regular polygon centred on the path.
