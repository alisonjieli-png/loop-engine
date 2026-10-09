# Extrude a polygon with holes

Turns a 2D outline with holes into a solid between y = 0 and y = height. Both caps are triangulated with the holes joined by bridges, walls are quads, and every hole becomes a tunnel. A taper below 1 shrinks the top face toward the origin.

## When to use it

Use it for plates, brackets, gaskets, signs, logos and letters, floor plans extruded into walls, cookie cutters and any 2.5D part made from an outline.

## How it works

Rings are reoriented (outer counter-clockwise, holes clockwise). meshkit's ear clipper joins each hole to the outer ring through a visible vertex and clips ears; the triangles serve as the top cap and, reversed, as the bottom cap. With taper s the volume is area * height * (1 + s + s^2) / 3.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `height` | float | m | `0.4` | 1e-06 to 1e+06 | Extrusion distance along +Y (the solid spans y = 0 to height). |
| `taper` | float | ratio | `1.0` | 0 to 100 | Scale of the top face about the origin (1 straight walls, below 1 inward slope). |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 extrude_polygon_holes.py --output model.gltf --height 0.4 --taper 1.0
```

From Python:

```python
from extrude_polygon_holes import extrude

washer = extrude([(1, 0), (0, 1), (-1, 0), (0, -1)], [[(0.3, 0), (0, -0.3), (-0.3, 0), (0, 0.3)]], height=0.1)
```

Entry points:

- `extrude(outer, holes=(), height=0.4, taper=1.0)`: A closed solid: the polygon at y = 0 (facing -Y), the same polygon scaled by ``taper`` at y = height (facing +Y) and quad walls. 2D (x, y) maps to (x, *, -y). Each hole adds one tunnel (genus = holes). Volume = area * height * (1 + taper + taper^2) / 3, which is area * height when taper = 1.
- `polygon_area(outer, holes=())`: Area of the polygon minus its holes (shoelace).
- `build(height=0.4, taper=1.0)`: The extruded demonstration plate (outline with a round and a square hole), flat shaded.
- `main(argv=None)`: Command line: write the extruded solid (.gltf or .obj) and print a JSON summary.

## Complexity

O(n^2) for the cap triangulation, n the total ring size.

## Outputs

- `.gltf`: the flat-shaded demonstration plate with POSITION and NORMAL
- `.obj`: the same solid as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `area`: `polygon_area(outer=[6 items], holes=[2 items])` gives value 2.98686 (tolerance 1e-12).
- `clockwise_square`: `extrude(outer=[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]], height=2)` gives 8 vertices; watertight; Euler characteristic 2; volume 2 (tolerance 1e-12); bounds [0.0, 0.0, -1.0] to [1.0, 2.0, 0.0].
- `plate_with_two_holes`: `extrude(outer=[6 items], holes=[2 items], height=0.4)` gives 60 vertices; 94 faces; watertight; genus 2; volume 1.19475 (tolerance 1e-12).
- `tapered`: `extrude(outer=[6 items], holes=[2 items], height=0.4, taper=0.5)` gives watertight; volume 0.696935 (tolerance 1e-12).

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Rings must be simple and the holes must lie inside the outer ring without touching each other; this is not checked. Taper scales about the origin, so off-centre shapes lean. No bevel or rounded edges.
