# Torus knot tube with parallel-transport frames

Builds a closed tube around the (p, q) torus knot, the curve that winds p times around the Y axis and q times around a torus tube. The frame is parallel transported along the curve and the angle left over at the end is spread evenly, so the tube closes without a twist seam.

## When to use it

Use it for knot sculpture and jewellery, decorative pipes and neon shapes, and as a closed genus-one test mesh with uneven curvature.

## How it works

The curve is sampled at evenly spaced parameters with analytic tangents. Starting from a normal perpendicular to the first tangent, each next normal is the previous one rotated by the rotation that carries one tangent to the next. After a full loop the normal differs from the start by the holonomy angle; that angle is undone gradually along the curve. Rings of sides vertices around each sample are joined into quads in both wrapping directions.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `p` | int | count | `2` | 1 to 64 | Turns around the Y axis (the torus' axis of symmetry). |
| `q` | int | count | `3` | 1 to 64 | Turns around the torus tube; p and q without a common factor give a knot. |
| `major_radius` | float | m | `1.0` | 1e-06 to 1e+06 | Radius of the torus the curve winds on. |
| `minor_radius` | float | m | `0.4` | 1e-06 to 1e+06 | Tube radius of that torus (how far the curve swings). |
| `tube_radius` | float | m | `0.1` | 1e-06 to 1e+06 | Radius of the swept circle; keep it below half the closest approach of the strands. |
| `segments` | int | count | `180` | 8 to 100000 | Samples along the curve. |
| `sides` | int | count | `12` | 3 to 1024 | Divisions around the tube. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 torus_knot.py --output model.gltf --p 2 --q 3 --major-radius 1.0 --minor-radius 0.4 --tube-radius 0.1 --segments 180 --sides 12
```

From Python:

```python
from torus_knot import torus_knot

knot = torus_knot(p=3, q=7, tube_radius=0.06, segments=600, sides=12)
```

Entry points:

- `knot_point(t, p=2, q=3, major_radius=1.0, minor_radius=0.4)`: Curve point at parameter t in [0, 2 pi): ((R + r cos qt) cos pt, r sin qt, -(R + r cos qt) sin pt).
- `knot_tangent(t, p=2, q=3, major_radius=1.0, minor_radius=0.4)`: Unit tangent of the curve from its analytic derivative.
- `transport_frames(tangents)`: Normals carried around a closed curve by rotating each one with the turn between consecutive tangents, then corrected by an even twist so the last normal meets the first.
- `torus_knot(p=2, q=3, major_radius=1.0, minor_radius=0.4, tube_radius=0.1, segments=180, sides=12)`: A closed tube along the (p, q) torus knot: segments * sides vertices and quads, torus topology.
- `main(argv=None)`: Command line: write the knot tube as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * sides).

## Outputs

- `.gltf`: one welded mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same tube as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `cinquefoil`: `torus_knot(p=2, q=5, segments=300, sides=8)` gives 2400 vertices; watertight; genus 1.
- `start_point`: `knot_point(t=0)` gives values matching the listed numbers (tolerance 1e-15).
- `trefoil`: `torus_knot()` gives 2160 vertices; 2160 faces; watertight; Euler characteristic 0; genus 1; volume 0.443276 (tolerance 0.0017731); surface area 9.17826 (tolerance 0.036713); unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The tube does not test for self-intersection: keep tube_radius below half the closest approach of the strands (true for the defaults). No texture coordinates. The volume and area checks compare with cross-section times curve length within 0.4 percent.
