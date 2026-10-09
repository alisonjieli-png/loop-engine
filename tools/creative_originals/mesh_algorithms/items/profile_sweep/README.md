# Profile sweep with scale and twist

Places a copy of a 2D profile at every path point, in a frame carried along the path, scaled linearly from 1 to end_scale and turned by an increasing twist, then joins the copies with quads and closes both ends with the triangulated profile.

## When to use it

Use it for mouldings and trims, horns and tentacles (taper and twist), handles and rails, twisted columns, cables with non-round sections and any extrusion along a curved path.

## How it works

Tangents come from central differences. The first frame takes any normal perpendicular to the first tangent; each next normal is the previous one rotated by the rotation carrying one tangent to the next. Profile x goes along the normal and y along the binormal. On a straight path the walls are planar trapezoids, so the volume is exactly area * length * (1 + s + s^2) / 3.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `profile` | str | name | `star` | one of `star`, `square`, `circle`, `cross` | Closed 2D cross-section. |
| `path` | str | name | `arc` | one of `arc`, `helix`, `line`, `s_curve` | 3D path the profile follows. |
| `end_scale` | float | ratio | `0.4` | 0 to 100 | Profile scale at the end of the path (1 at the start, linear in between). |
| `twist` | float | degrees | `90.0` | -36000 to 36000 | Total rotation of the profile about the path from start to end. |
| `steps` | int | count | `64` | 1 to 100000 | Path samples minus one. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 profile_sweep.py --output model.gltf --profile star --path arc --end-scale 0.4 --twist 90.0 --steps 64
```

From Python:

```python
from profile_sweep import sweep, demo_profile, demo_path

horn = sweep(demo_profile("circle", 0.2), demo_path("arc", 48), end_scale=0.1, twist=0.0)
```

Entry points:

- `demo_profile(name='star', size=0.3)`: A counter-clockwise closed 2D profile: five-point star, square, 24-gon circle or plus-shaped cross.
- `demo_path(name='arc', steps=64)`: ``steps`` + 1 points along a demonstration path.
- `sweep(profile, path, end_scale=1.0, twist=0.0, caps=True)`: A mesh of len(path) rings of len(profile) vertices; ring k is the profile scaled by lerp(1, end_scale, k / (n - 1)) and turned by twist * k / (n - 1) degrees, placed in a frame carried along the path by the rotation between consecutive tangents. Caps triangulate the profile, so the result is closed. Profile x maps to the frame normal and profile y to the binormal; the profile is made counter-clockwise first.
- `build(profile='star', path='arc', end_scale=0.4, twist=90.0, steps=64)`: The swept demonstration solid, flat shaded so profile corners stay crisp.
- `main(argv=None)`: Command line: write the swept solid (.gltf or .obj) and print a JSON summary.

## Complexity

O(path points * profile points).

## Outputs

- `.gltf`: the flat-shaded swept solid with POSITION and NORMAL
- `.obj`: the same solid as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `helix_volume`: `sweep(profile=demo_profile(...), path=demo_path(...))` gives watertight; volume 2.54491 (tolerance 0.00508981).
- `straight_frustum`: `sweep(profile=[4 items], path=[5 items], end_scale=0.5)` gives watertight; volume 1.16667 (tolerance 1e-12).
- `straight_prism`: `sweep(profile=[4 items], path=[5 items])` gives 20 vertices; 20 faces; watertight; volume 2 (tolerance 1e-12).
- `twisted_star_on_arc`: `sweep(profile=demo_profile(...), path=demo_path(...), end_scale=0.4, twist=90)` gives 650 vertices; 656 faces; watertight; Euler characteristic 2.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

The profile must be a simple polygon; tight bends with a large profile fold the walls through each other (not detected). Twisted walls are non-planar quads split along their shorter diagonal. Frames are transported by the turn between tangents (first order), so very coarse paths drift.
