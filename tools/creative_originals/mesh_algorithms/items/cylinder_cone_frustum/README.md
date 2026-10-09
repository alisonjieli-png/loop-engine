# Cylinder, cone, frustum and pipe

Generates the straight solids of revolution around Y in one function: with equal radii a cylinder, with one radius zero a cone, otherwise a frustum, and with an inner radius a pipe whose ends are annuli. Caps can be left off for an open tube.

## When to use it

Use it for columns, posts, cups, buckets, nozzles, pipes, washers and lamp shades, or as the building block of procedural props.

## How it works

The side is a band of quads between two rings (or triangles to one apex vertex per segment for a cone). Side normals tilt by the slope between the radii. Caps get their own ring of vertices with a flat normal and planar texture coordinates; with a bore the caps are rings of quads and an inner wall faces the axis. All faces are planar, so the volume equals the revolved profile's exactly.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `bottom_radius` | float | m | `0.6` | 0 to 1e+06 | Outer radius at the bottom (y = -height / 2); 0 makes a cone pointing down. |
| `top_radius` | float | m | `0.3` | 0 to 1e+06 | Outer radius at the top (y = +height / 2); 0 makes a cone; equal radii make a cylinder. |
| `height` | float | m | `1.2` | 1e-06 to 1e+06 | Distance between the bottom and top planes. |
| `segments` | int | count | `32` | 3 to 4096 | Divisions around the Y axis. |
| `inner_radius` | float | m | `0.12` | 0 to 1e+06 | Radius of a straight bore along Y; 0 for a solid. Must be below both outer radii. |
| `caps` | bool | flag | `True` | any to any | Close the ends; without caps the result is an open tube (or two tubes with a bore). |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 cylinder_cone_frustum.py --output model.gltf --bottom-radius 0.6 --top-radius 0.3 --height 1.2 --segments 32 --inner-radius 0.12 --caps True
```

From Python:

```python
from cylinder_cone_frustum import frustum

pipe = frustum(bottom_radius=0.2, top_radius=0.2, height=2.0, inner_radius=0.15)
cone = frustum(bottom_radius=0.5, top_radius=0.0, height=1.0, inner_radius=0.0)
```

Entry points:

- `frustum(bottom_radius=0.6, top_radius=0.3, height=1.2, segments=32, inner_radius=0.12, caps=True)`: A straight solid of revolution around Y, centred at the origin, with outward faces.
- `main(argv=None)`: Command line: write the solid as .gltf or .obj and print a JSON summary.

## Complexity

O(segments).

## Outputs

- `.gltf`: one mesh with POSITION, NORMAL and TEXCOORD_0, indexed triangles
- `.obj`: the same solid as Wavefront OBJ with polygon caps

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `bored_frustum`: `frustum()` gives 260 vertices; 128 faces; 256 triangles; watertight after welding coincident vertices; genus 1; volume 0.732666 (tolerance 1e-12); surface area 5.70882 (tolerance 1e-12); unit vertex normals.
- `cone`: `frustum(bottom_radius=1, top_radius=0, height=1, segments=24, inner_radius=0)` gives 73 vertices; 46 triangles; watertight after welding coincident vertices; volume 1.03528 (tolerance 1e-12); surface area 7.51712 (tolerance 1e-12).
- `cylinder`: `frustum(bottom_radius=0.5, top_radius=0.5, height=2, segments=64, inner_radius=0)` gives watertight after welding coincident vertices; volume 1.56827 (tolerance 1e-12); surface area 7.84894 (tolerance 1e-12); bounds [-0.5, -1.0, -0.5] to [0.5, 1.0, 0.5].
- `open_tube`: `frustum(inner_radius=0, caps=False)` gives 66 vertices; 32 faces; 2 boundary loops after welding; Euler characteristic 0 after welding.
- `solid_frustum`: `frustum(inner_radius=0)` gives 130 vertices; 34 faces; 124 triangles; watertight after welding coincident vertices; Euler characteristic 2 after welding; volume 0.786604 (tolerance 1e-12); surface area 4.89539 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Only straight sides (no curved profile; see a lathe for that) and a constant-radius bore. Caps and walls own separate vertices for sharp shading, so closed results are watertight after welding. A cone apex holds one vertex per segment.
