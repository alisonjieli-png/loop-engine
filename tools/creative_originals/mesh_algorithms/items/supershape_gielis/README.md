# 3D supershape from the Gielis superformula

Builds a closed 3D supershape: the horizontal superformula curve r1 and the vertical curve r2 multiply like the radius of a sphere in latitude and longitude. Small changes of the eight exponents and symmetries give stars, flowers, shells, cushions and crystals.

## When to use it

Use it for procedural plants, flowers and seed pods, alien creatures, gems and decorative props, or to explore a large family of shapes from a few numbers.

## How it works

Longitude t and latitude p are sampled evenly; the point is (r1(t) cos t r2(p) cos p, r2(p) sin p, -r1(t) sin t r2(p) cos p) times the size. The poles are single vertices joined by triangle fans and normals are angle weighted.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `m1` | float | symmetry | `7.0` | 0 to 100 | Rotational symmetry of the horizontal curve (lobes around Y). |
| `n1` | float | exponent | `0.2` | 0.01 to 100 | Overall exponent of the horizontal curve. |
| `n2` | float | exponent | `1.7` | 0 to 100 | Cosine term exponent of the horizontal curve. |
| `n3` | float | exponent | `1.7` | 0 to 100 | Sine term exponent of the horizontal curve. |
| `m2` | float | symmetry | `7.0` | 0 to 100 | Symmetry of the vertical (latitude) curve. |
| `p1` | float | exponent | `0.2` | 0.01 to 100 | Overall exponent of the vertical curve. |
| `p2` | float | exponent | `1.7` | 0 to 100 | Cosine term exponent of the vertical curve. |
| `p3` | float | exponent | `1.7` | 0 to 100 | Sine term exponent of the vertical curve. |
| `size` | float | m | `1.0` | 1e-06 to 1e+06 | Uniform scale of the result. |
| `segments` | int | count | `64` | 3 to 4096 | Divisions around the Y axis. |
| `rings` | int | count | `32` | 2 to 4096 | Divisions from pole to pole. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 supershape_gielis.py --output model.gltf --m1 7.0 --n1 0.2 --n2 1.7 --n3 1.7 --m2 7.0 --p1 0.2 --p2 1.7 --p3 1.7 --size 1.0 --segments 64 --rings 32
```

From Python:

```python
from supershape_gielis import supershape

flower = supershape(m1=5, n1=0.3, n2=0.3, n3=0.3, m2=1, p1=1, p2=1, p3=1)
```

Entry points:

- `superformula(angle, m=7.0, n1=0.2, n2=1.7, n3=1.7, a=1.0, b=1.0)`: Gielis superformula radius r(angle) = (|cos(m angle / 4) / a|^n2 + |sin(m angle / 4) / b|^n3)^(-1 / n1).
- `supershape(m1=7.0, n1=0.2, n2=1.7, n3=1.7, m2=7.0, p1=0.2, p2=1.7, p3=1.7, size=1.0, segments=64, rings=32)`: A welded 3D supershape: 2 + (rings - 1) * segments vertices and segments * rings outward faces.
- `main(argv=None)`: Command line: write the supershape as .gltf or .obj and print a JSON summary.

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

- `default`: `supershape()` gives 1986 vertices; 2048 faces; watertight; Euler characteristic 2; unit vertex normals.
- `sphere_when_symmetry_is_zero`: `supershape(m1=0, n1=1, n2=1, n3=1, m2=0, p1=1, p2=1, p3=1, segments=16, rings=8)` gives every vertex at distance 1 from [0.0, 0.0, 0.0]; volume 3.9266 (tolerance 1e-09); surface area 12.1667 (tolerance 1e-09).
- `square_curve`: `superformula(angle=0.785398, m=4, n1=1, n2=1, n3=1)` gives value 0.707107 (tolerance 1e-15).
- `unit_circle`: `superformula(angle=0.7, m=0, n1=2, n2=2, n3=2)` gives value 1 (tolerance 1e-15).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Some parameter sets make the radius very large or undefined at certain angles (an error is raised when both terms vanish); very small n1 values give spiky shapes with thin faces. The surface can intersect itself for extreme values. No texture coordinates.
