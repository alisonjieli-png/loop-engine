# Capsule with hemispherical caps

Builds a capsule centred at the origin along Y: a straight part of the given length between two hemispheres of the same radius. Texture v runs along the profile by arc length so the texture is not stretched on the caps.

## When to use it

Use it for character and projectile colliders, pills, rounded rods and handles, or as a cheap rounded limb in procedural creatures.

## How it works

The (r, y) profile has cap_rings steps along each quarter circle; the two equator rings bound the straight part. The profile is revolved into segments columns with a repeated seam column and one pole vertex per segment. Normals point from the nearer hemisphere centre (or straight out on the cylinder), and the exact mesh volume follows from revolving the profile polygon.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `0.5` | 1e-06 to 1e+06 | Radius of the cylinder and of both hemispheres. |
| `length` | float | m | `1.0` | 0 to 1e+06 | Length of the straight part; the total height is length + 2 * radius. |
| `segments` | int | count | `32` | 3 to 4096 | Divisions around the Y axis. |
| `cap_rings` | int | count | `8` | 1 to 2048 | Rings in each hemisphere from the pole to the equator. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 capsule.py --output model.gltf --radius 0.5 --length 1.0 --segments 32 --cap-rings 8
```

From Python:

```python
from capsule import capsule

body = capsule(radius=0.35, length=1.1, segments=24, cap_rings=6)
```

Entry points:

- `capsule_profile(radius=0.5, length=1.0, cap_rings=8)`: The (r, y) profile from the north pole to the south pole: quarter arcs joined by the straight part.
- `capsule(radius=0.5, length=1.0, segments=32, cap_rings=8)`: A capsule along Y centred at the origin: 2 segments + 2 cap_rings (segments + 1) vertices and 4 cap_rings segments triangles, with unit normals and UVs (v from the north pole by profile length).
- `main(argv=None)`: Command line: write the capsule as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * cap_rings).

## Outputs

- `.gltf`: one mesh with POSITION, NORMAL and TEXCOORD_0, indexed triangles
- `.obj`: the same capsule as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `default`: `capsule()` gives 592 vertices; 1024 triangles; watertight after welding coincident vertices; Euler characteristic 2 after welding; volume 1.2956 (tolerance 1e-09); surface area 6.25297 (tolerance 1e-09); bounds [-0.5, -1.0, -0.5] to [0.5, 1.0, 0.5]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; texture coordinates spanning [0.0, 0.0] to [1.0, 1.0].
- `sphere_when_length_is_zero`: `capsule(radius=1, length=0, segments=16, cap_rings=4)` gives 168 vertices; volume 3.9266 (tolerance 1e-12); every vertex at distance 1 from [0.0, 0.0, 0.0].

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The equator rows are doubled (one ring for each hemisphere), so the straight part has exactly one row of quads. The seam and the pole vertices are duplicated for texture coordinates, so the mesh is closed after welding.
