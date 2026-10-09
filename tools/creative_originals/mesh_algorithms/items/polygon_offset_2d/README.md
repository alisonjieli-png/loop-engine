# Polygon offset with miter, round or bevel joins

Moves every edge of a polygon outward (positive distance) or inward (negative) and rebuilds the corners: overlapping offset edges meet at their intersection; separating ones are joined by a miter point, an arc around the original corner or a straight bevel.

## When to use it

Use it for outlines and strokes around shapes, safety margins and keep-out zones, cutter compensation in toolpaths, wall thickness from floor-plan outlines and shrinking regions for insets.

## How it works

The polygon is made counter-clockwise so the right-hand normal points out. At each corner the sign of the turn and of the distance decide whether the offset edges overlap or open a gap. A miter longer than miter_limit times the distance falls back to a bevel. The result is tested for crossing edges and positive area.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `distance` | float | m | `0.25` | -1e+06 to 1e+06 | Offset distance: positive grows the polygon, negative shrinks it. |
| `join` | str | name | `round` | one of `round`, `miter`, `bevel` | How offset edges meet at corners that open a gap. |
| `arc_segments` | int | count | `8` | 1 to 4096 | Segments per 90 degrees of a round join. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 polygon_offset_2d.py --output model.gltf --distance 0.25 --join round --arc-segments 8
```

From Python:

```python
from polygon_offset_2d import offset_polygon

margin = offset_polygon([(0, 0), (3, 0), (3, 2), (0, 2)], 0.25, join="round")
```

Entry points:

- `offset_polygon(polygon, distance, join='round', arc_segments=8, miter_limit=4.0)`: The offset outline, counter-clockwise. Each edge moves ``distance`` along its outward normal; where the moved edges overlap (a corner turning against the offset) they meet at their line intersection, and where they open a gap the ``join`` fills it: the line intersection (miter, limited to miter_limit * |distance|, beyond which it bevels), an arc around the corner (round) or the straight gap (bevel). Raises MeshError when an edge would vanish or turn around (offset_collapses) or the result would cross itself (offset_self_intersects).
- `build(distance=0.25, join='round', arc_segments=8)`: A flat band between the demonstration polygon and its offset (the offset outside, or inside when the distance is negative), in the XZ plane facing +Y.
- `main(argv=None)`: Command line: write the offset band (.gltf or .obj) and print a JSON summary.

## Complexity

O(n^2) including the self-intersection check.

## Outputs

- `.gltf`: a flat band between the demonstration polygon and its offset, in the XZ plane facing +Y
- `.obj`: the same band as Wavefront OBJ

Axes and units: +Y up, metres; 2D (x, y) maps to (x, 0, -y).

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `bevel`: `offset_polygon(polygon=[4 items], distance=0.5, join="bevel")` gives 8 points; polygon area 8.5 (tolerance 1e-12).
- `concave_inward`: `offset_polygon(polygon=[6 items], distance=-0.25, join="miter")` gives polygon area 1.25 (tolerance 1e-12); 6 points.
- `inward`: `offset_polygon(polygon=[4 items], distance=-0.5)` gives polygon area 1 (tolerance 1e-12); points matching the listed coordinates.
- `miter`: `offset_polygon(polygon=[4 items], distance=0.5, join="miter")` gives 4 points; polygon area 9 (tolerance 1e-12).
- `round`: `offset_polygon(polygon=[4 items], distance=0.5, join="round", arc_segments=8)` gives 36 points; polygon area 8.78036 (tolerance 1e-12); simple polygons.
- `too_far_inward`: `offset_polygon(polygon=[4 items], distance=-1.5)` is refused with MeshError `offset_collapses`.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Offsets that make edges vanish or cross are refused rather than cleaned up (no splitting into several polygons). Holes are not handled; offset each ring separately with the opposite sign. Round joins are polylines of arc_segments chords per right angle.
