# Superellipsoid superquadric

Builds a superellipsoid: sign(c)|c|^e terms replace the cosines and sines of an ellipsoid. The north_south exponent shapes the vertical profile and east_west the horizontal cross-section. superellipsoid_volume gives the smooth solid's exact volume.

## When to use it

Use it for rounded boxes, cushions, pebbles, cylinders with soft edges, diamond and star shapes, and in shape fitting where a few parameters describe a whole family of solids.

## How it works

Polar angle and azimuth are sampled evenly; each point is (a S(sin p, e1) S(cos t, e2), b S(cos p, e1), -c S(sin p, e1) S(sin t, e2)) with S(w, e) = sign(w) |w|^e. Poles are single vertices with triangle fans. The exact volume is 2 a b c e1 e2 B(e1/2 + 1, e1) B(e2/2, e2/2) with B the beta function.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `size_x` | float | m | `1.0` | 1e-06 to 1e+06 | Semi-axis along X. |
| `size_y` | float | m | `0.8` | 1e-06 to 1e+06 | Semi-axis along Y (up). |
| `size_z` | float | m | `1.0` | 1e-06 to 1e+06 | Semi-axis along Z. |
| `north_south` | float | exponent | `0.6` | 0.01 to 4 | Exponent e1 of the latitude profile: below 1 squarer, 1 round, above 1 pinched. |
| `east_west` | float | exponent | `0.3` | 0.01 to 4 | Exponent e2 of the horizontal cross-section: below 1 squarer, 1 round, 2 diamond. |
| `segments` | int | count | `48` | 3 to 4096 | Divisions around the Y axis. |
| `rings` | int | count | `24` | 2 to 4096 | Divisions from pole to pole. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 superellipsoid.py --output model.gltf --size-x 1.0 --size-y 0.8 --size-z 1.0 --north-south 0.6 --east-west 0.3 --segments 48 --rings 24
```

From Python:

```python
from superellipsoid import superellipsoid, superellipsoid_volume

pebble = superellipsoid(1.0, 0.4, 0.7, north_south=0.8, east_west=0.6)
print(superellipsoid_volume(1.0, 0.4, 0.7, 0.8, 0.6))
```

Entry points:

- `superellipsoid_point(polar, azimuth, size_x=1.0, size_y=0.8, size_z=1.0, north_south=0.6, east_west=0.3)`: Surface point at polar angle ``polar`` from +Y and azimuth from +X toward -Z (signed powers of cos, sin).
- `superellipsoid(size_x=1.0, size_y=0.8, size_z=1.0, north_south=0.6, east_west=0.3, segments=48, rings=24)`: A welded superellipsoid: 2 + (rings - 1) * segments vertices, segments * rings faces, outward winding.
- `superellipsoid_volume(size_x=1.0, size_y=0.8, size_z=1.0, north_south=0.6, east_west=0.3)`: Exact volume of the smooth surface: 2 a b c e1 e2 B(e1 / 2 + 1, e1) B(e2 / 2, e2 / 2), B the beta function.
- `main(argv=None)`: Command line: write the superellipsoid as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * rings).

## Outputs

- `.gltf`: one welded mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same solid as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `converges_to_formula`: `superellipsoid(north_south=1, east_west=0.3, segments=128, rings=64)` gives watertight; volume 4.13876 (tolerance 0.00620813).
- `default`: `superellipsoid()` gives 1106 vertices; 1152 faces; watertight; Euler characteristic 2; bounds [-1.0, -0.8, -1.0] to [1.0, 0.8, 1.0]; unit vertex normals.
- `ellipsoid_exact`: `superellipsoid(size_x=1, size_y=0.8, size_z=1.2, north_south=1, east_west=1, segments=40, rings=20)` gives watertight; volume 3.98007 (tolerance 1e-09).
- `formula`: `superellipsoid_volume(north_south=1, east_west=0.3)` gives value 4.13876 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Even angle sampling crowds vertices near sharp edges and leaves flat sides coarse for small exponents; exponents near 0 produce nearly degenerate thin faces. No texture coordinates. Normals are mesh normals, not the analytic surface normals.
