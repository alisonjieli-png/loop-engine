# Threaded rod with a trapezoidal helical thread

Builds a threaded rod along Y: the surface radius at angle theta and height y follows a trapezoidal profile of the phase y / pitch - theta / (2 pi), which makes a right-hand helical thread. The two ends are closed by polygon caps.

## When to use it

Use it for bolts, screws, threaded rods, jar and bottle necks and lead screws in mechanical scenes, or as a starting point for 3D-printable threads after setting real dimensions.

## How it works

A grid of rings at even heights holds segments vertices each, at the radius minor + (major - minor) times the profile: zero on the root flat, linear up the flank, one on the crest flat and linear down. Because every horizontal slice is the same shape turned, the solid's exact volume is length times pi times the mean of r squared over the profile.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `major_radius` | float | m | `0.2` | 1e-06 to 1e+06 | Radius at the thread crest. |
| `minor_radius` | float | m | `0.16` | 1e-06 to 1e+06 | Radius at the thread root; below major_radius. |
| `pitch` | float | m | `0.1` | 1e-06 to 1e+06 | Axial distance between neighbouring crests (one turn for a single start). |
| `length` | float | m | `0.8` | 1e-06 to 1e+06 | Length of the rod along Y. |
| `crest` | float | fraction | `0.15` | 0 to 0.9 | Fraction of the pitch that is flat at the crest. |
| `root` | float | fraction | `0.25` | 0 to 0.9 | Fraction of the pitch that is flat at the root; crest + root < 1. |
| `segments` | int | count | `32` | 3 to 4096 | Divisions around the rod. |
| `samples_per_pitch` | int | count | `8` | 4 to 1000 | Axial rows per pitch. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 screw_thread.py --output model.gltf --major-radius 0.2 --minor-radius 0.16 --pitch 0.1 --length 0.8 --crest 0.15 --root 0.25 --segments 32 --samples-per-pitch 8
```

From Python:

```python
from screw_thread import screw_thread

bolt = screw_thread(major_radius=0.05, minor_radius=0.042, pitch=0.0125, length=0.3)
```

Entry points:

- `thread_profile(phase, crest=0.15, root=0.25)`: Height of the thread in [0, 1] at ``phase`` (fraction of the pitch): root flat, rising flank, crest flat, falling flank, each flank (1 - crest - root) / 2 of the pitch.
- `screw_thread(major_radius=0.2, minor_radius=0.16, pitch=0.1, length=0.8, crest=0.15, root=0.25, segments=32, samples_per_pitch=8)`: A closed threaded rod centred at the origin along Y: (rows + 1) * segments vertices, rows * segments quads and two polygon caps, where rows = ceil(length / pitch * samples_per_pitch). The radius at angle theta and height y is minor + (major - minor) * profile(y / pitch - theta / 2 pi): a right-hand thread.
- `main(argv=None)`: Command line: write the threaded rod as .gltf or .obj and print a JSON summary.

## Complexity

O(segments * length / pitch * samples_per_pitch).

## Outputs

- `.gltf`: one welded mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same rod as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `crest_flat`: `thread_profile(phase=1.6)` gives value 1 (tolerance 0).
- `default`: `screw_thread()` gives 2080 vertices; 2050 faces; watertight; Euler characteristic 2; volume 0.0797092 (tolerance 0.000239128); unit vertex normals; inside [-0.2, -0.4, -0.2] to [0.2, 0.4, 0.2].
- `flank_middle`: `thread_profile(phase=0.4)` gives value 0.5 (tolerance 1e-12).
- `root_flat`: `thread_profile(phase=0.1)` gives value 0 (tolerance 0).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

A single right-hand start; the ends are cut flat through the thread without a chamfer. The flanks are sampled on a fixed grid, so the crest and root corners are only as sharp as the axial sampling. Dimensions are free numbers, not tied to a thread standard.
