# Rounded box with filleted edges

Builds a box with every edge and corner rounded: the surface of the inner box (shrunk by the radius) grown by a sphere of that radius. rounded_box_volume gives the exact volume of the smooth shape.

## When to use it

Use it for furniture, phones and devices, keyboard keys, buttons, cushions and any boxy prop that should catch light on its edges.

## How it works

Each axis gets lattice lines spaced by a quarter circle across the rounded bands and evenly across the flat middle. Every lattice point on the box surface moves to the nearest point of the inner box plus the radius times the unit direction from there, which lands on the rounded surface; the direction is also the normal. Lattice points are shared along box edges, so the mesh is closed.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `size_x` | float | m | `2.0` | 1e-06 to 1e+06 | Overall size along X. |
| `size_y` | float | m | `1.0` | 1e-06 to 1e+06 | Overall size along Y. |
| `size_z` | float | m | `1.4` | 1e-06 to 1e+06 | Overall size along Z. |
| `radius` | float | m | `0.25` | 0 to 1e+06 | Rounding radius; at most half the smallest size. |
| `bevel_segments` | int | count | `6` | 1 to 256 | Divisions across each rounded edge (a quarter circle). |
| `flat_segments` | int | count | `2` | 1 to 1024 | Divisions across each flat face strip. |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 rounded_box.py --output model.gltf --size-x 2.0 --size-y 1.0 --size-z 1.4 --radius 0.25 --bevel-segments 6 --flat-segments 2
```

From Python:

```python
from rounded_box import rounded_box, rounded_box_volume

key = rounded_box(0.018, 0.008, 0.018, radius=0.002, bevel_segments=4)
print(rounded_box_volume(0.018, 0.008, 0.018, 0.002))
```

Entry points:

- `rounded_box_volume(size_x=2.0, size_y=1.0, size_z=1.4, radius=0.25)`: Exact volume of the smooth rounded box: inner box, six slabs, twelve quarter cylinders, one sphere.
- `rounded_box(size_x=2.0, size_y=1.0, size_z=1.4, radius=0.25, bevel_segments=6, flat_segments=2)`: A closed rounded box centred at the origin with unit normals.
- `main(argv=None)`: Command line: write the rounded box as .gltf or .obj and print a JSON summary.

## Complexity

O(face lattice size).

## Outputs

- `.gltf`: one welded mesh with POSITION and NORMAL, indexed triangles
- `.obj`: the same box as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `default`: `rounded_box()` gives 1178 vertices; 1176 faces; watertight; Euler characteristic 2; volume 2.58486 (tolerance 0.0103395); bounds [-1.0, -0.5, -0.7] to [1.0, 0.5, 0.7]; unit vertex normals; vertex normals agree with the face winding on 100 percent of triangles.
- `sharp_box`: `rounded_box(radius=0)` gives 26 vertices; 24 faces; watertight; volume 2.8 (tolerance 1e-12); surface area 12.4 (tolerance 1e-12).
- `sphere_limit`: `rounded_box(size_x=1, size_y=1, size_z=1, radius=0.5)` gives watertight; every vertex at distance 0.5 from [0.0, 0.0, 0.0].
- `volume_formula`: `rounded_box_volume()` gives value 2.58486 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

One radius for every edge; no per-edge radii or chamfers. No texture coordinates. The rounded bands use a lattice pulled onto the surface, so their quads are not exactly even.
