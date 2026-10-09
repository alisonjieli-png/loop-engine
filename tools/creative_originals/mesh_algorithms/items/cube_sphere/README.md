# Cube sphere with equal-area mapping

Builds a sphere from a cube whose six faces are divided into n x n quads. The lattice points are shared along cube edges and corners, so the result is one closed quad mesh with 6 n^2 + 2 vertices, and each point is mapped onto the sphere.

## When to use it

Use it for planets and terrains wrapped on a sphere, for cube-map texturing and for any sphere that should be made of quads with similar sizes. The quad layout also subdivides well.

## How it works

Lattice points with integer coordinates on the surface of an n-cube are scaled to [-1, 1]. The equal_area mapping sends (x, y, z) to (x sqrt(1 - y^2/2 - z^2/2 + y^2 z^2 / 3), and cyclic), which lands exactly on the unit sphere and spreads cells more evenly than dividing by the length. Faces of the six cube sides are wound so their normals point outward.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `1.0` | 1e-06 to 1e+06 | Distance from the centre to every vertex. |
| `divisions` | int | count | `12` | 1 to 512 | Quads along each cube edge; 6 * divisions^2 quads in total. |
| `mapping` | str | name | `equal_area` | one of `equal_area`, `normalized` | Cube to sphere mapping: the polynomial mapping with more even cells, or plain normalization. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 cube_sphere.py --output model.gltf --radius 1.0 --divisions 12 --mapping equal_area
```

From Python:

```python
from cube_sphere import cube_sphere, face_area_ratio

planet = cube_sphere(radius=6.0, divisions=24)
print(face_area_ratio(planet))
```

Entry points:

- `cube_to_sphere(point, mapping='equal_area')`: Map a point on the surface of the cube [-1, 1]^3 to the unit sphere.
- `cube_sphere(radius=1.0, divisions=12, mapping='equal_area')`: A welded cube sphere: 6 n^2 + 2 vertices and 6 n^2 outward quads (n = divisions), unit normals.
- `face_area_ratio(mesh)`: Largest face area divided by the smallest: 1 for perfectly even cells.
- `main(argv=None)`: Command line: write the cube sphere as .gltf or .obj and print a JSON summary.

## Complexity

O(divisions^2). Lattice points are shared through a dictionary keyed by their integer coordinates.

## Outputs

- `.gltf`: one welded mesh with POSITION and NORMAL, quads split into triangles
- `.obj`: the same sphere as Wavefront OBJ with quad faces

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `corner_maps_to_diagonal`: `cube_to_sphere(point=[1.0, 1.0, 1.0])` gives values matching the listed numbers (tolerance 1e-15).
- `equal_area_default`: `cube_sphere(radius=1, divisions=12)` gives 866 vertices; 864 faces; 864 quads; watertight; Euler characteristic 2; every vertex at distance 1 from [0.0, 0.0, 0.0]; bounds [-1.0, -1.0, -1.0] to [1.0, 1.0, 1.0]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles.
- `even_cells`: `face_area_ratio(mesh=cube_sphere(...))` gives at most 1.2.
- `normalized_cells_are_uneven`: `face_area_ratio(mesh=cube_sphere(...))` gives at least 4.
- `single_division`: `cube_sphere(radius=3, divisions=1)` gives 8 vertices; 6 faces; watertight; every vertex at distance 3 from [0.0, 0.0, 0.0].

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

No texture coordinates in the welded mesh; per-face cube-map coordinates need the six faces split apart. Cells are even but not equal (largest over smallest area about 1.16 at 12 divisions with the equal_area mapping, about 4.2 with plain normalization).
