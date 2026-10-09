# Rotation-minimizing frames by double reflection

Carries a frame along a curve so it turns only as much as the tangent forces it to: no twist about the tangent. Each step reflects the frame in the plane bisecting the chord, then in the plane that maps the reflected tangent onto the next tangent.

## When to use it

Use it to orient sweeps, ribbons, rails, roller-coaster tracks and cable meshes, to keep a camera's roll stable along a path, or to measure the twist of Frenet frames.

## How it works

For consecutive points x_i, x_(i+1) with v1 = x_(i+1) - x_i, the frame (r, t) is reflected by I - 2 v1 v1^T / (v1 . v1); with v2 = t_(i+1) - t_reflected, a second reflection by I - 2 v2 v2^T / (v2 . v2) gives the next normal. For a helix the frame turns against the Frenet frame at minus the torsion per unit length, which the checks confirm.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `curve` | str | name | `trefoil` | one of `trefoil`, `helix`, `wave` | Demonstration curve the ribbon follows. |
| `width` | float | m | `0.25` | 0.001 to 100 | Ribbon width across the frame normal. |
| `samples` | int | count | `300` | 4 to 100000 | Samples along the curve. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 rotation_minimizing_frames.py --output model.gltf --curve trefoil --width 0.25 --samples 300
```

From Python:

```python
from rotation_minimizing_frames import double_reflection_frames, ribbon

points = [(t * 0.1, 0.0, (t * 0.1) ** 2) for t in range(50)]
frames = double_reflection_frames(points)
strip = ribbon(points, frames, width=0.2)
```

Entry points:

- `double_reflection_frames(points, tangents=None, normal=None)`: Frames (tangent, normal, binormal) along sampled points by double reflection (Wang, Juttler, Zheng and Liu 2008): reflect the previous frame in the bisector plane of the chord, then in the plane that maps the reflected tangent onto the next tangent. Fourth-order accurate for smooth curves. Without ``tangents``, central differences of an open polyline are used; without ``normal``, one perpendicular to the first tangent is chosen.
- `frenet_frames(points)`: Frenet frames from finite differences (normal toward the centre of curvature); undefined where the curve is straight, where the previous normal is kept.
- `frame_normals(points, closed=False)`: Just the normals of the rotation-minimizing frames for points with central-difference tangents.
- `closing_twist(points, frames)`: For a closed curve: the angle (radians, about the first tangent) between the first normal and the last frame carried once more across the closing chord. Zero means the frames join without a twist.
- `twist_between(frames_a, frames_b)`: Signed angle (radians) of each normal of ``frames_b`` relative to the matching normal of ``frames_a``, about the tangent of ``frames_a``.
- `demo_curve(curve='trefoil', samples=300)`: Points of a demonstration curve: a closed trefoil knot, a three-turn helix or an open wave.
- `ribbon(points, frames, width=0.25, closed=False, spread_twist=True)`: A two-sided strip across each frame's binormal (the strip faces along the normal); a closed curve can spread its closing twist evenly so the strip joins without a jump.
- `build(curve='trefoil', width=0.25, samples=300)`: The ribbon along the demonstration curve, oriented by rotation-minimizing frames.
- `main(argv=None)`: Command line: write the ribbon (.gltf or .obj) and print a JSON summary.

## Complexity

O(n) for n samples.

## Outputs

- `.gltf`: a two-sided ribbon along the demonstration curve, oriented by the frames
- `.obj`: the same ribbon as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `helix_twist_equals_torsion`: `twist_between(frames_a=frenet_frames(...), frames_b=double_reflection_frames(...))` (selecting `400`) gives value -2.28584 (tolerance 1e-06).
- `planar_circle_keeps_normal`: `frame_normals(points=[64 items], closed=True)` gives 64 points; points matching the listed coordinates.
- `planar_loop_closes`: `closing_twist(points=[64 items], frames=double_reflection_frames(...))` gives value 0 (tolerance 1e-09).
- `ribbon`: `build()` gives 600 vertices; 300 faces; manifold.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Frames are only as good as the sampling: the method is fourth-order accurate between samples but cannot recover detail the samples miss. Tangents from central differences are used when none are given. A closed curve generally does not return to its starting frame; ribbon() spreads that angle evenly.
