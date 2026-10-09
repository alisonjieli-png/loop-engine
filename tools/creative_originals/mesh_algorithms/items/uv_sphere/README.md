# UV sphere with texture seam and pole fans

Builds a sphere from rings of latitude and segments of longitude. Every vertex lies exactly on the sphere, normals are the unit position vectors, and texture coordinates run u along longitude and v from the north pole (v = 0) to the south pole (v = 1).

## When to use it

Pick it when a texture is laid out as an equirectangular (longitude by latitude) image, such as a planet map, a sky texture applied to a ball or a globe. For an even triangle size, prefer an icosphere or a cube sphere.

## How it works

Row r sits at polar angle pi r / rings from +Y and column s at longitude 2 pi s / segments, measured from +X toward -Z so that u increases to the right seen from outside. The last column repeats the first with u = 1, which forms the texture seam. Each pole holds one vertex per segment with u at the segment centre, so the pole triangles do not share one stretched texel. Interior cells are planar quads (isosceles trapezoids); cells at the poles are triangles. Vertices: 2 segments + (rings - 1)(segments + 1). Triangles: 2 segments (rings - 1).

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `1.0` | 1e-06 to 1e+06 | Distance from the centre to every vertex. |
| `segments` | int | count | `32` | 3 to 2048 | Divisions around the Y axis (longitude). |
| `rings` | int | count | `16` | 2 to 2048 | Divisions from the north pole to the south pole (latitude). |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 uv_sphere.py --output model.gltf --radius 1.0 --segments 32 --rings 16
```

From Python:

```python
import meshkit
from uv_sphere import uv_sphere

sphere = uv_sphere(radius=1.0, segments=32, rings=16)
print(len(sphere.vertices), sphere.triangle_count())
meshkit.write_gltf("sphere.gltf", [sphere])
```

Entry points:

- `uv_sphere(radius=1.0, segments=32, rings=16)`: A UV sphere centred at the origin with unit normals, texture coordinates and outward faces.
- `main(argv=None)`: Command line: write the sphere as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * rings). One vertex and one face per grid cell; memory grows the same way.

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

- `bipyramid`: `uv_sphere(radius=1, segments=3, rings=2)` gives 10 vertices; 6 faces; 6 triangles; watertight after welding coincident vertices; Euler characteristic 2 after welding; volume 0.866025 (tolerance 1e-09); surface area 5.80948 (tolerance 1e-09); every vertex at distance 1 from [0.0, 0.0, 0.0]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; texture coordinates spanning [0.0, 0.0] to [1.0, 1.0].
- `default`: `uv_sphere(radius=1, segments=32, rings=16)` gives 559 vertices; 512 faces; 960 triangles; watertight after welding coincident vertices; Euler characteristic 2 after welding; volume 4.12194 (tolerance 1e-09); surface area 12.4657 (tolerance 1e-09); every vertex at distance 1 from [0.0, 0.0, 0.0]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; texture coordinates spanning [0.0, 0.0] to [1.0, 1.0].
- `fine_scaled`: `uv_sphere(radius=2.5, segments=48, rings=24)` gives 1223 vertices; 1152 faces; 2208 triangles; watertight after welding coincident vertices; Euler characteristic 2 after welding; volume 64.9839 (tolerance 1.5625e-08); surface area 78.2598 (tolerance 6.25e-09); every vertex at distance 2.5 from [0.0, 0.0, 0.0]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; texture coordinates spanning [0.0, 0.0] to [1.0, 1.0].

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The seam and the pole vertices are duplicated for texture coordinates, so the mesh is closed only after welding coincident vertices. Pole triangles are thin and the faces are not equal in area; use an icosphere or a cube sphere for even tessellation. The polygon volume and area are below the true sphere's and approach them as segments and rings grow.
