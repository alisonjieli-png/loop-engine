# Torus with wrapped texture coordinates

Builds a torus whose tube centre circles the Y axis. Vertices carry unit normals and texture coordinates: u follows the ring and v goes around the tube, both from 0 to 1.

## When to use it

Use it for rings, donuts, tyres, pipes bent into loops, and as the standard genus-one surface when testing mesh tools.

## How it works

Row j sits at tube angle 2 pi j / sides starting at the outer equator; column i at ring angle 2 pi i / segments from +X toward -Z. The last row and column repeat the first so texture coordinates can reach 1. Each quad is planar (an isosceles trapezoid), so the exact volume of the mesh is n sin(2 pi / n) times the first moment of the tube cross-section polygon.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `major_radius` | float | m | `1.0` | 1e-06 to 1e+06 | Distance from the Y axis to the centre of the tube. |
| `minor_radius` | float | m | `0.35` | 1e-06 to 1e+06 | Radius of the tube; below major_radius for a ring torus. |
| `segments` | int | count | `48` | 3 to 4096 | Divisions around the Y axis. |
| `sides` | int | count | `24` | 3 to 4096 | Divisions around the tube. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 torus.py --output model.gltf --major-radius 1.0 --minor-radius 0.35 --segments 48 --sides 24
```

From Python:

```python
from torus import torus

ring = torus(major_radius=2.0, minor_radius=0.25, segments=96, sides=16)
```

Entry points:

- `torus(major_radius=1.0, minor_radius=0.35, segments=48, sides=24)`: A torus centred at the origin around +Y with unit normals, UVs and outward quads.
- `main(argv=None)`: Command line: write the torus as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * sides).

## Outputs

- `.gltf`: one mesh with POSITION, NORMAL and TEXCOORD_0, indexed triangles
- `.obj`: the same torus as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `coarse`: `torus(major_radius=2, minor_radius=0.5, segments=4, sides=3)` gives 20 vertices; 12 faces; watertight after welding coincident vertices; genus 1; volume 2.59808 (tolerance 1e-12); surface area 25.0334 (tolerance 1e-12).
- `default`: `torus()` gives 1225 vertices; 1152 faces; watertight after welding coincident vertices; Euler characteristic 0 after welding; genus 1; volume 2.3837 (tolerance 1e-09); surface area 13.7535 (tolerance 1e-09); unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; texture coordinates spanning [0.0, 0.0] to [1.0, 1.0]; bounds [-1.35, -0.35, -1.35] to [1.35, 0.35, 1.35].

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The texture seam duplicates one row and one column, so the mesh is closed only after welding. Self-intersecting (horn and spindle) tori, with the minor radius at or above the major radius, are not handled specially. The polygon volume is below the smooth torus's.
