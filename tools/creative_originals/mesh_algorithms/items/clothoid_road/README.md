# Clothoid transition road

Builds the centre line of a road bend whose curvature rises linearly from 0 to 1 / radius over a clothoid, stays constant on a circular arc, and falls back over a second clothoid, then lays a flat ribbon with asphalt and edge-line colours along it.

## When to use it

Use it for roads, railway and roller-coaster track layouts, race circuits and camera dollies where the steering must change smoothly instead of jumping at the start of an arc.

## How it works

Within a transition, position is the Fresnel integral pair x = integral cos(u^2 / 2A^2), y = integral sin(u^2 / 2A^2) with A^2 = radius * transition, evaluated by its power series and rotated onto the current heading; the falling transition uses the same integrals in reverse. Arcs use the circle formula and straights the heading directly.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `8.0` | 0.1 to 1e+06 | Radius of the circular arc in the middle of the bend. |
| `transition` | float | m | `6.0` | 0 to 1e+06 | Length of each clothoid, over which curvature grows linearly from 0 to 1 / radius. |
| `arc_angle` | float | degrees | `60.0` | 0 to 300 | Turn of the circular arc between the two clothoids. |
| `width` | float | m | `3.0` | 0.01 to 1000 | Road width. |
| `step` | float | m | `0.5` | 0.01 to 100 | Arc-length spacing of the road cross-sections. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 clothoid_road.py --output model.gltf --radius 8.0 --transition 6.0 --arc-angle 60.0 --width 3.0 --step 0.5
```

From Python:

```python
from clothoid_road import centre_line, road

line = centre_line(radius=40.0, transition=20.0, arc_angle=45.0, step=1.0)
ribbon = road(40.0, 20.0, 45.0, width=7.0, step=1.0)
```

Entry points:

- `clothoid_point(s, scale)`: (x, y, heading) on the unit-direction clothoid at arc length s: x = integral cos(u^2 / (2 A^2)) du, y = integral sin(u^2 / (2 A^2)) du from 0 to s with A = ``scale``, heading s^2 / (2 A^2). Integrated by the power series of the Fresnel integrals (converges for every s).
- `curvature_at(s, transition=6.0, radius=8.0, arc_length=0.0)`: Curvature of the road centre line at distance s along the bend: rising linearly over the first clothoid, 1 / radius along the arc, falling over the second clothoid, 0 elsewhere.
- `centre_line(radius=8.0, transition=6.0, arc_angle=60.0, step=0.5, lead=6.0)`: Points (x, y) and headings of the road centre line, starting with a straight of length ``lead`` along +x, integrating the piecewise-linear curvature exactly segment by segment (clothoid series inside the transitions, circles on the arc).
- `road(radius=8.0, transition=6.0, arc_angle=60.0, width=3.0, step=0.5)`: A flat road ribbon in the XZ plane (2D y maps to -z) with asphalt colour and white edge lines.
- `main(argv=None)`: Command line: write the road ribbon (.gltf or .obj) and print a JSON summary.

## Complexity

O(length / step) points, each a short power series.

## Outputs

- `.gltf`: the road ribbon with POSITION, NORMAL and COLOR_0 (asphalt with white edge lines)
- `.obj`: the same ribbon as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `bend_end`: `centre_line()` (selecting `-1`) gives values matching the listed numbers (tolerance 1e-06).
- `curvature_rises_linearly`: `curvature_at(s=3)` gives value 0.0625 (tolerance 1e-15).
- `fresnel_point`: `clothoid_point(s=6, scale=6.9282)` gives values matching the listed numbers (tolerance 1e-10).
- `road_ribbon`: `road()` gives 264 vertices; 195 faces; vertex colours; every vertex on the plane n . p = 0, n = [0.0, 1.0, 0.0]; 1 boundary loops.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

A flat road in one plane: no banking, crown or elevation profile. One left-hand bend between two straights; chain several calls for longer layouts. The series is evaluated in double precision, accurate to about 1e-10 m for transitions of a few hundred metres.
