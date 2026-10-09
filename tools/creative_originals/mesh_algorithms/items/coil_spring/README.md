# Coil spring along a helix

Builds a coil spring: a circular wire swept along a helix around Y, with a polygon cap at each end. The frame along the helix is rotation minimizing, so the wire's vertex rows do not twist around the wire.

## When to use it

Use it for springs in mechanical models, suspension and click-pen props, coiled cables and decorative spirals.

## How it works

A helix of radius R and pitch P has a constant Frenet frame relative to its own turning and constant torsion b / (R^2 + b^2) with b = P / (2 pi). Turning the Frenet normal back by the accumulated torsion gives the rotation-minimizing normal exactly. Each sample holds a ring of sides vertices; the end rings are copied for flat caps facing along the tangent.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `coil_radius` | float | m | `0.5` | 1e-06 to 1e+06 | Distance from the Y axis to the wire centre. |
| `pitch` | float | m | `0.25` | 0 to 1e+06 | Rise per turn; keep it above twice the wire radius so turns do not touch. |
| `turns` | float | turns | `6.0` | 0.01 to 10000 | Number of turns (fractions allowed). |
| `wire_radius` | float | m | `0.05` | 1e-06 to 1e+06 | Radius of the wire cross-section. |
| `steps_per_turn` | int | count | `36` | 3 to 100000 | Samples along the helix per turn. |
| `sides` | int | count | `10` | 3 to 1024 | Divisions around the wire. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 coil_spring.py --output model.gltf --coil-radius 0.5 --pitch 0.25 --turns 6.0 --wire-radius 0.05 --steps-per-turn 36 --sides 10
```

From Python:

```python
from coil_spring import coil_spring

spring = coil_spring(coil_radius=0.3, pitch=0.12, turns=10, wire_radius=0.03)
```

Entry points:

- `helix_frame(t, coil_radius=0.5, pitch=0.25)`: (tangent, normal, binormal) at helix angle t; the normal is the Frenet normal turned back by the accumulated torsion, which makes the frame rotation-minimizing (no twist about the tangent).
- `coil_spring(coil_radius=0.5, pitch=0.25, turns=6.0, wire_radius=0.05, steps_per_turn=36, sides=10)`: A closed spring mesh centred at the origin along Y.
- `main(argv=None)`: Command line: write the spring as .gltf or .obj and print a JSON summary.

## Complexity

O(turns * steps_per_turn * sides).

## Outputs

- `.gltf`: one mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same spring as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `default`: `coil_spring()` gives 2190 vertices; 2162 faces; watertight after welding coincident vertices; Euler characteristic 2 after welding; volume 0.138931 (tolerance 0.00111145); unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles; inside [-0.55, -0.8, -0.55] to [0.55, 0.8, 0.55].
- `flat_coil`: `coil_spring(pitch=0, turns=0.5, steps_per_turn=8, sides=4)` gives 28 vertices; 18 faces; watertight after welding coincident vertices.
- `frame_at_start`: `helix_frame(t=0)` (selecting `1`) gives values matching the listed numbers (tolerance 1e-15).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Turns touch or pass through each other when the pitch is below twice the wire radius; nothing checks this. The volume check allows 0.8 percent below cross-section times helix length, the loss from straight segments and tilted rings at 36 steps per turn. Ends are cut square to the wire (no ground flat ends). No texture coordinates. Cap vertices are separate from the wire ends, so the mesh is closed after welding.
