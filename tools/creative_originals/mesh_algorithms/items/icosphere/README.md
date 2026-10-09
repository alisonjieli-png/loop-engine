# Icosphere by recursive subdivision

Builds a sphere from a regular icosahedron. Each subdivision level splits every triangle into four through its edge midpoints and pushes the new vertices out to the sphere, giving 10 * 4^n + 2 vertices and 20 * 4^n nearly equal triangles.

## When to use it

Use it where triangle size should be even over the whole sphere: physics and collision spheres, planets with procedural surfaces, displacement and particle emission. For an equirectangular texture use a UV sphere instead.

## How it works

The twelve vertices are the corners of three mutually perpendicular golden rectangles, scaled to the requested radius. Faces are the triples of vertices that are pairwise one edge length apart, wound so their normals point away from the centre. Subdivision keeps a map from each undirected edge to its midpoint vertex so neighbouring triangles share it, then normalizes the midpoint onto the unit sphere. Normals are the unit position vectors.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `1.0` | 1e-06 to 1e+06 | Distance from the centre to every vertex. |
| `subdivisions` | int | count | `3` | 0 to 7 | Times each triangle is split into four; 10 * 4^n + 2 vertices. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 icosphere.py --output model.gltf --radius 1.0 --subdivisions 3
```

From Python:

```python
import meshkit
from icosphere import icosphere

ball = icosphere(radius=0.5, subdivisions=4)
meshkit.write_gltf("ball.gltf", [ball])
```

Entry points:

- `icosahedron(radius=1.0)`: The regular icosahedron inscribed in a sphere of ``radius``: 12 vertices and 20 outward triangles.
- `icosphere(radius=1.0, subdivisions=3)`: An icosphere with 10 * 4^n + 2 vertices and 20 * 4^n triangles, every vertex on the sphere.
- `main(argv=None)`: Command line: write the icosphere as .gltf or .obj and print a JSON summary.

## Complexity

O(20 * 4^subdivisions). Each level multiplies the triangle count by four; midpoints are shared through an edge map.

## Outputs

- `.gltf`: one mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same sphere as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `icosahedron_exact`: `icosphere(radius=1, subdivisions=0)` gives 12 vertices; 20 faces; watertight; Euler characteristic 2; convex; volume 2.53615 (tolerance 1e-12); surface area 9.57454 (tolerance 1e-12); every vertex at distance 1 from [0.0, 0.0, 0.0].
- `one_level`: `icosphere(radius=1, subdivisions=1)` gives 42 vertices; 80 faces; watertight.
- `three_levels`: `icosphere(radius=2, subdivisions=3)` gives 642 vertices; 1280 faces; watertight; Euler characteristic 2; convex; every vertex at distance 2 from [0.0, 0.0, 0.0]; edge lengths between 0.26 and 0.34; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

No texture coordinates: an icosphere has no seam-free UV layout; add a spherical projection if needed. Triangles are close to equal but not identical in size (edge lengths vary by about 20 percent at three levels). The polygon volume is below the true sphere's.
