# Lathe revolution with partial angles

Turns a 2D (r, y) profile into a solid of revolution around Y. Points on the axis become single vertices; a partial angle adds the two cut faces so the solid stays closed. revolved_volume gives the exact volume of the polygonal result.

## When to use it

Use it for vases, bowls, cups, chess pieces, bottles, lamp bases, table legs, turned wood and any machined part with rotational symmetry, and for cutaway views with a partial angle.

## How it works

Every profile point sweeps segments + 1 positions (one fewer for a full turn, which wraps). Quads join neighbouring profile points; where a corner lies on the axis the quad becomes a triangle. Each swept chord is straight, so the solid's volume is n sin(angle / n) times the integral of r over the profile polygon closed along the axis.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `profile` | str | name | `vase` | one of `vase`, `bowl`, `pawn`, `spindle` | Demonstration (r, y) profile. |
| `segments` | int | count | `48` | 3 to 4096 | Divisions of the swept angle. |
| `angle` | float | degrees | `360.0` | 1 to 360 | Swept angle; below 360 the cut sides are closed with the profile polygon. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 lathe_revolve.py --output model.gltf --profile vase --segments 48 --angle 360.0
```

From Python:

```python
from lathe_revolve import lathe, revolved_volume

profile = [(0.0, 0.0), (0.4, 0.0), (0.3, 0.5), (0.35, 1.0), (0.0, 1.0)]
cup = lathe(profile, segments=64)
print(revolved_volume(profile, 64))
```

Entry points:

- `demo_profile(name='vase')`: An (r, y) polyline from bottom to top; r = 0 at an end closes the solid on the axis there.
- `lathe(profile, segments=48, angle=360.0)`: Revolve ``profile`` about Y; points with r = 0 become single vertices. A full turn welds the seam; a partial turn adds both cut faces (the profile closed along the axis) and is closed when both profile ends lie on the axis. Faces point outward for a profile listed from bottom to top with r >= 0.
- `revolved_volume(profile, segments=48, angle=360.0)`: Exact volume of the lathe solid: segments * sin(angle / segments) * |first moment of the profile polygon closed along the axis| (each profile point sweeps straight chords, not circular arcs).
- `build(profile='vase', segments=48, angle=360.0)`: The smooth-shaded lathe solid of a demonstration profile.
- `main(argv=None)`: Command line: write the revolved solid (.gltf or .obj) and print a JSON summary.

## Complexity

O(profile points * segments).

## Outputs

- `.gltf`: the revolved demonstration profile with POSITION and NORMAL (double-sided for open profiles)
- `.obj`: the same surface as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `cylinder`: `lathe(profile=[[0.0, 0.0], [1.0, 0.0], [1.0, 2.0], [0.0, 2.0]], segments=64)` gives 130 vertices; 192 faces; watertight; volume 6.2731 (tolerance 1e-12); surface area 18.8344 (tolerance 1e-12).
- `half_turn`: `lathe(profile=[[0.0, 0.0], [1.0, 0.0], [1.0, 2.0], [0.0, 2.0]], segments=16, angle=180)` gives watertight; volume 3.12145 (tolerance 1e-12).
- `open_vase`: `lathe(profile=demo_profile(...))` gives 1201 vertices; 1200 faces; 1 boundary loops; manifold.
- `sphere`: `lathe(profile=[17 items], segments=32)` gives watertight; Euler characteristic 2; volume 4.12194 (tolerance 1e-12); every vertex at distance 1 from [0.0, 0.0, 0.0].
- `spindle`: `lathe(profile=[13 items], segments=48)` gives watertight; volume 1.02642 (tolerance 1e-12).
- `volume_formula`: `revolved_volume(profile=[[0.0, 0.0], [1.0, 0.0], [1.0, 2.0], [0.0, 2.0]], segments=16, angle=180)` gives value 3.12145 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Profile points need r >= 0 and should go from bottom to top; a profile that crosses the axis or itself gives an invalid solid. Open profiles (not ending on the axis) give open surfaces. Points on the axis collapse to single vertices, so pole faces are triangles.
