# Catmull-Clark subdivision surface

Applies Catmull-Clark subdivision to any polygon mesh. Every step replaces each face of n corners with n quads, moves the original vertices toward a smooth limit and keeps open boundaries as cubic B-spline curves.

## When to use it

Use it to turn a coarse modelling cage into a smooth quad mesh: characters, product shapes, rounded props. It accepts triangles and n-gons, so a hard-surface blockout can be smoothed directly.

## How it works

Face points are face centroids. An interior edge point averages the edge ends and the two adjacent face points; a boundary edge point is the midpoint. An interior vertex of valence n moves to (Q + 2R + (n - 3)P) / n, where Q averages the adjacent face points and R the adjacent edge midpoints. A boundary vertex moves to (6P + two boundary neighbours) / 8 and a corner with two edges stays fixed. Each corner of each face becomes one quad (vertex, next edge point, face point, previous edge point), which keeps the winding.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `cage` | str | name | `torus` | one of `cube`, `torus`, `plane`, `l_block` | Control cage to subdivide. |
| `levels` | int | count | `3` | 0 to 6 | Number of subdivision steps; each step multiplies the face count by about four. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 catmull_clark_subdivision.py --output model.gltf --cage torus --levels 3
```

From Python:

```python
import meshkit
from catmull_clark_subdivision import catmull_clark, cage

smooth = catmull_clark(cage("l_block"), levels=3)
print(len(smooth.vertices), len(smooth.faces))
meshkit.write_gltf("smooth.gltf", [smooth])
```

Entry points:

- `catmull_clark(mesh, levels=1)`: Subdivide ``levels`` times; every output face is a quad and normals are angle weighted.
- `cage(name='torus')`: A demonstration control cage: 'cube', 'torus' (4 x 4 square ring), 'plane' (open 2 x 2 grid with a raised centre) or 'l_block' (an extruded L whose caps are hexagons).
- `build(cage='torus', levels=3)`: The subdivided demonstration cage the command line writes.
- `main(argv=None)`: Command line: write the subdivided cage as .gltf or .obj and print a JSON summary.

## Complexity

O(4^levels * F). Each level turns V, E, F into V + E + F vertices and one quad per face corner.

## Outputs

- `.gltf`: one mesh with POSITION, NORMAL and the attributes listed above, indexed triangles
- `.obj`: the same mesh as Wavefront OBJ with positions, normals and polygon faces

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `cube_one_level`: `catmull_clark(mesh=cage(...), levels=1)` gives 26 vertices; 24 faces; 24 quads; watertight; Euler characteristic 2; bounds [-0.5, -0.5, -0.5] to [0.5, 0.5, 0.5]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles.
- `cube_two_levels`: `catmull_clark(mesh=meshkit.box(), levels=2)` gives 98 vertices; 96 faces; watertight; Euler characteristic 2; inside [-0.5, -0.5, -0.5] to [0.5, 0.5, 0.5].
- `hexagon_caps`: `catmull_clark(mesh=cage(...), levels=1)` gives 38 vertices; 36 faces; 36 quads; watertight; Euler characteristic 2.
- `open_plane`: `catmull_clark(mesh=cage(...), levels=1)` gives 25 vertices; 16 faces; 1 boundary loops; 16 boundary edges; Euler characteristic 1; manifold; bounds [-1.0, 0.0, -1.0] to [1.0, 0.28125, 1.0].
- `torus_cage`: `catmull_clark(mesh=cage(...), levels=1)` gives 64 vertices; 64 faces; watertight; Euler characteristic 0; genus 1.
- `triangle_cage`: `catmull_clark(mesh=meshkit.tetrahedron(), levels=1)` gives 14 vertices; 12 faces; watertight; Euler characteristic 2.
- `zero_levels`: `catmull_clark(mesh=meshkit.box(), levels=0)` gives 8 vertices; 6 faces; volume 1 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

No crease or corner sharpness tags beyond fixed valence-two boundary corners. Faces may be triangles, quads or larger polygons, but non-manifold edges (three or more faces) are treated as boundary midpoints. Output quads are generally not planar and are split along their shorter diagonal on export. Positions follow the standard rules; the limit surface is not evaluated.
