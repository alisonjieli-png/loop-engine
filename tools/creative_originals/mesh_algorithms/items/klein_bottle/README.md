# Klein bottle figure-eight immersion

Builds the figure-eight Klein bottle: a figure-eight curve swept around a circle while turning half a revolution, which closes up with a reflection. Every edge has two faces and no edge is on a boundary, yet no outward side exists.

## When to use it

Use it as mathematical sculpture, in topology teaching material, or to test that mesh tools cope with closed surfaces that cannot be consistently oriented.

## How it works

Points are sampled on a u_segments x v_segments grid of the immersion. Going once around u maps v to -v, so the quads of the last column join the first column at mirrored rows. Vertex normals are angle weighted from the faces.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `radius` | float | m | `2.0` | 1 to 1e+06 | Radius of the centre circle before scaling; above 1 keeps the figure eight off the axis. |
| `scale` | float | m | `0.5` | 1e-06 to 1e+06 | Uniform scale applied to the whole surface. |
| `u_segments` | int | count | `80` | 3 to 100000 | Divisions around the centre circle. |
| `v_segments` | int | count | `24` | 4 to 100000 | Divisions around the figure-eight cross-section. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 klein_bottle.py --output model.gltf --radius 2.0 --scale 0.5 --u-segments 80 --v-segments 24
```

From Python:

```python
from klein_bottle import klein_bottle

bottle = klein_bottle(radius=2.5, scale=0.4)
```

Entry points:

- `figure_eight_point(u, v, radius=2.0)`: Point of the figure-eight immersion at angles u (around the centre circle) and v (around the eight).
- `klein_bottle(radius=2.0, scale=0.5, u_segments=80, v_segments=24)`: A closed figure-eight Klein bottle: u_segments * v_segments vertices and as many quads.
- `main(argv=None)`: Command line: write the surface as .gltf or .obj and print a JSON summary.

## Complexity

O(u_segments * v_segments).

## Outputs

- `.gltf`: one double-sided mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same surface as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `coarse`: `klein_bottle(radius=3, scale=1, u_segments=8, v_segments=6)` gives 48 vertices; 48 faces; closed; not consistently oriented; Euler characteristic 0.
- `default`: `klein_bottle()` gives 1920 vertices; 1920 faces; closed; manifold; not consistently oriented; Euler characteristic 0; 1 connected components; unit vertex normals.
- `seam_point`: `figure_eight_point(u=0, v=0, radius=2)` gives values matching the listed numbers (tolerance 1e-15).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The figure-eight immersion passes through itself along one circle, as every Klein bottle in three dimensions must; the mesh does not split faces there. There is no consistent winding, so normals flip across one seam and the surface should be drawn double-sided.
