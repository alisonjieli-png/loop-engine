# Kochanek-Bartels tension, continuity and bias spline

Builds an interpolating curve from cubic Hermite segments. At each key the incoming and outgoing tangents mix the differences to the previous and next keys with factors from tension (length), continuity (corner sharpness) and bias (overshoot direction).

## When to use it

Use it for animation paths and value curves: tension 1 for linear-looking motion with eased keys, negative tension for looser curves, bias for overshoot or anticipation, continuity for deliberate corners.

## How it works

With differences a = P_i - P_(i-1) and b = P_(i+1) - P_i, the outgoing tangent is (1-t)(1+b)(1+c)/2 a + (1-t)(1-b)(1-c)/2 b and the incoming one swaps the continuity sign. Each segment is the Hermite cubic between two keys with the outgoing and incoming tangents.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `tension` | float | ratio | `0.0` | -1 to 1 | Tangent length: 1 gives straight segments, -1 rounder curves. |
| `continuity` | float | ratio | `0.0` | -1 to 1 | Difference between incoming and outgoing tangents: away from 0 makes corners. |
| `bias` | float | ratio | `0.0` | -1 to 1 | Tangent direction: positive leans toward the previous key (overshoot), negative toward the next. |
| `samples_per_segment` | int | count | `16` | 1 to 10000 | Points per segment. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 kochanek_bartels_spline.py --output model.gltf --tension 0.0 --continuity 0.0 --bias 0.0 --samples-per-segment 16
```

From Python:

```python
from kochanek_bartels_spline import tcb_spline

path = tcb_spline([(0, 0, 0), (1, 2, 0), (3, 1, 0), (4, 3, 0)], tension=0.3, bias=0.2)
```

Entry points:

- `hermite(p0, p1, m0, m1, t)`: Cubic Hermite point from p0 (t = 0) to p1 (t = 1) with end tangents m0 and m1.
- `tcb_tangents(previous, current, following, tension=0.0, continuity=0.0, bias=0.0)`: (incoming, outgoing) tangents at ``current`` from the Kochanek-Bartels formulas.
- `tcb_spline(keys, tension=0.0, continuity=0.0, bias=0.0, samples_per_segment=16)`: Points through every key (open curve; the end keys repeat their neighbour difference). With all three parameters 0 the curve is the uniform Catmull-Rom spline; with tension 1 every segment is straight.
- `build(tension=0.0, continuity=0.0, bias=0.0, samples_per_segment=16)`: Tubes for the chosen setting (gold) and, for comparison, tension 0.8 (blue) through the same keys.
- `main(argv=None)`: Command line: write the spline tubes (.gltf or .obj) and print a JSON summary.

## Complexity

O(keys * samples_per_segment).

## Outputs

- `.gltf`: tubes along the chosen spline and along a tension 0.8 version for comparison
- `.obj`: the same tubes as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `default_tangents`: `tcb_tangents(previous=[0.0, 0.0, 0.0], current=[1.0, 0.0, 0.0], following=[1.0, 2.0, 0.0])` gives values matching the listed numbers (tolerance 1e-15).
- `display`: `build()` gives 2 meshes; watertight.
- `full_continuity_corner`: `tcb_tangents(previous=[0.0, 0.0, 0.0], current=[1.0, 0.0, 0.0], following=[1.0, 2.0, 0.0], continuity=1)` gives values matching the listed numbers (tolerance 1e-15).
- `hermite_end`: `hermite(p0=[0.0, 0.0, 0.0], p1=[1.0, 1.0, 0.0], m0=[1.0, 0.0, 0.0], m1=[0.0, 1.0, 0.0], t=1)` gives values matching the listed numbers (tolerance 0).
- `tension_one_is_straight`: `tcb_spline(keys=[4 items], tension=1, samples_per_segment=4)` gives 13 points; points matching the listed coordinates.
- `zero_parameters_are_catmull_rom`: `tcb_spline(keys=[4 items], samples_per_segment=2)` (selecting `3`) gives values matching the listed numbers (tolerance 1e-14).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Keys are equally spaced in time; uneven key times would need the tangent scaling of the original paper, which is not applied. Large continuity values make visible corners by design. Open ends repeat the neighbour difference.
