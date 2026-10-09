# Platonic solids with exact edge length

Builds the tetrahedron, cube, octahedron, dodecahedron and icosahedron with an exact edge length. Faces are polygons (triangles, squares, pentagons) found from the vertices alone and wound outward.

## When to use it

Use them for dice and game pieces, crystals and gems, teaching and reference models, and as seeds for subdivision, truncation and Conway operators.

## How it works

Vertices come from the standard coordinates: alternate cube corners, the cube, the axis points, cube corners plus three golden rectangles, and three golden rectangles. A plane through three vertices that has every vertex on one side is a face; the vertices on it are sorted by angle around the face centre so the polygon is counter-clockwise seen from outside.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `solid` | str | name | `all` | one of `all`, `tetrahedron`, `cube`, `octahedron`, `dodecahedron`, `icosahedron` | Which solid to write; 'all' places the five in a row along X. |
| `edge` | float | m | `1.0` | 1e-06 to 1e+06 | Edge length of every solid. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 platonic_solids.py --output model.gltf --solid all --edge 1.0
```

From Python:

```python
from platonic_solids import platonic_solid

d20 = platonic_solid("icosahedron", edge=0.02)
```

Entry points:

- `solid_vertices(name, edge=1.0)`: Vertex coordinates of a Platonic solid centred at the origin with the given edge length.
- `hull_faces(vertices)`: Faces of a convex polyhedron given only its vertices: each plane through three vertices with all vertices on one side is a face; its vertices are ordered counter-clockwise seen from outside.
- `platonic_solid(name='dodecahedron', edge=1.0)`: One Platonic solid: exact vertices, polygon faces (triangles, squares or pentagons), outward winding.
- `build(solid='all', edge=1.0)`: The flat-shaded solid, or all five side by side along X, as the command line writes them.
- `main(argv=None)`: Command line: write the solids as .gltf or .obj and print a JSON summary.

## Complexity

O(V^4) face finding for V <= 20 vertices.

## Outputs

- `.gltf`: one flat-shaded mesh per solid (or all five along X), POSITION and NORMAL
- `.obj`: the same solids as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `cube`: `platonic_solid(name="cube", edge=1)` gives 8 vertices; 6 faces; Euler characteristic 2; watertight; convex; volume 1 (tolerance 1e-12); surface area 6 (tolerance 1e-12); every vertex at distance 0.866025 from [0.0, 0.0, 0.0].
- `dodecahedron`: `platonic_solid(name="dodecahedron", edge=1)` gives 20 vertices; 12 faces; Euler characteristic 2; watertight; convex; volume 7.66312 (tolerance 1e-12); surface area 20.6457 (tolerance 1e-12); every vertex at distance 1.40126 from [0.0, 0.0, 0.0].
- `icosahedron`: `platonic_solid(name="icosahedron", edge=1)` gives 12 vertices; 20 faces; Euler characteristic 2; watertight; convex; volume 2.18169 (tolerance 1e-12); surface area 8.66025 (tolerance 1e-12); every vertex at distance 0.951057 from [0.0, 0.0, 0.0].
- `octahedron`: `platonic_solid(name="octahedron", edge=1)` gives 6 vertices; 8 faces; Euler characteristic 2; watertight; convex; volume 0.471405 (tolerance 1e-12); surface area 3.4641 (tolerance 1e-12); every vertex at distance 0.707107 from [0.0, 0.0, 0.0].
- `tetrahedron`: `platonic_solid(name="tetrahedron", edge=1)` gives 4 vertices; 4 faces; Euler characteristic 2; watertight; convex; volume 0.117851 (tolerance 1e-12); surface area 1.73205 (tolerance 1e-12); every vertex at distance 0.612372 from [0.0, 0.0, 0.0].

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Only the five regular convex solids; no star polyhedra or Archimedean solids. Face finding checks every vertex triple, which is fine for these sizes but not for large point sets.
