# Moebius strip and twisted bands

Builds a band that winds once around the Y axis while its cross-section turns by k half twists. With an odd k the last column joins the first upside down, giving a one-sided surface with one boundary loop; with an even k the band has two sides and two edges.

## When to use it

Use it for sculpture and jewellery, conveyor and race-track gags, puzzle props, and as a test surface for tools that must handle non-orientable meshes.

## How it works

Vertices sit on a segments x (strips + 1) grid of the parameterization without a duplicated column. The quads of the last column connect to the first column directly for even twists and to the mirrored column for odd ones. Normals are the cross product of the two tangent directions of the parameterization.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `1.0` | 1e-06 to 1e+06 | Radius of the centre circle around the Y axis. |
| `width` | float | m | `0.5` | 1e-06 to 1e+06 | Width of the band; keep it below twice the radius. |
| `half_twists` | int | count | `1` | 0 to 64 | Half turns of the band along the loop; odd values give a one-sided band. |
| `segments` | int | count | `120` | 3 to 100000 | Divisions along the loop. |
| `strips` | int | count | `6` | 1 to 1000 | Divisions across the width. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 mobius_strip.py --output model.gltf --radius 1.0 --width 0.5 --half-twists 1 --segments 120 --strips 6
```

From Python:

```python
from mobius_strip import mobius_strip

band = mobius_strip(radius=1.0, width=0.4, half_twists=3)
```

Entry points:

- `band_point(angle, offset, radius=1.0, half_twists=1)`: Point at loop angle ``angle`` (radians, from +X toward -Z) and signed offset across the band.
- `mobius_strip(radius=1.0, width=0.5, half_twists=1, segments=120, strips=6)`: A twisted band of segments * (strips + 1) vertices and segments * strips quads, with no seam.
- `main(argv=None)`: Command line: write the band as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * strips).

## Outputs

- `.gltf`: one double-sided mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same band as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `flat_ring`: `mobius_strip(half_twists=0, segments=64, strips=1)` gives every vertex on the plane n . p = 0, n = [0.0, 1.0, 0.0]; 2 boundary loops; consistently oriented.
- `moebius`: `mobius_strip()` gives 840 vertices; 720 faces; manifold; not consistently oriented; 1 boundary loops; Euler characteristic 0; surface area 3.14991 (tolerance 0.0125996); unit vertex normals.
- `three_half_twists`: `mobius_strip(half_twists=3, segments=60, strips=2)` gives 180 vertices; 120 faces; not consistently oriented; 1 boundary loops.
- `two_half_twists`: `mobius_strip(half_twists=2)` gives 840 vertices; 720 faces; consistently oriented; 2 boundary loops; Euler characteristic 0.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

A one-sided surface has no consistent winding: faces disagree across one seam column and the normals there flip, so render it double-sided (the material is marked so). Very wide bands (width near twice the radius) self-intersect. The area check tolerance covers the flat-quad approximation.
