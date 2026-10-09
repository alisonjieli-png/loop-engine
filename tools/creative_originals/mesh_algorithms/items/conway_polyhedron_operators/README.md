# Conway polyhedron operators

Applies Conway polyhedron operators to a seed. The topology follows the operator rules exactly (for example truncating the icosahedron gives the 60-vertex, 32-face football); the geometry is placed on the unit sphere and relaxed toward planar faces.

## When to use it

Use it for geodesic domes and spheres, footballs, gems and crystals, architectural lattices and decorative shells, or to generate many related polyhedra from short strings.

## How it works

Faces around each vertex are ordered by walking directed edges: from a face, the next face around the vertex owns the edge from the vertex back to that face's previous corner. Dual takes face centres and these cycles; ambo uses edge midpoints; kis raises a fan on each face; gyro splits each n-gon into n pentagons with two points on each edge. The other operators are compositions (t = dkd, j = da, e = aa, o = daa, s = dg). After each operator the vertices move toward the planes of their faces and are rescaled to unit mean radius.

## Parameters

Command line options (the Python functions take the same names as keyword arguments):

| Name | Type | Unit | Default | Range | Meaning |
|---|---|---|---|---|---|
| `notation` | str | notation | `tI` | any to any | Operators read right to left, then a seed: T C O D I, Pn (prism) or An (antiprism), for example tI, sC, dkD. |
| `relax` | int | iterations | `40` | 0 to 10000 | Planarizing iterations after each operator (0 keeps raw centroids on the unit sphere). |

## Use it

Command line, with `meshkit.py` in the same folder (writes `.gltf` or `.obj` and prints a one-line JSON summary):

```
python3 conway_polyhedron_operators.py --output model.gltf --notation tI --relax 40
```

From Python:

```python
from conway_polyhedron_operators import conway

football = conway("tI")
snub_cube = conway("sC")
```

Entry points:

- `seed(name)`: Seed polyhedron (vertices on the unit sphere, outward faces): T, C, O, D, I, Pn or An (n >= 3).
- `dual(vertices, faces)`: Dual: one vertex per face (its centroid on the unit sphere), one face per vertex (its faces in order).
- `ambo(vertices, faces)`: Ambo (rectify): one vertex per edge midpoint; a face for each old face and each old vertex.
- `kis(vertices, faces)`: Kis: raise a vertex over every face centre and replace the face with a fan of triangles.
- `gyro(vertices, faces)`: Gyro: every n-gon becomes n pentagons around a new centre, with two new vertices on each edge.
- `apply_operator(letter, vertices, faces)`: One operator: d dual, a ambo, k kis, j join (da), t truncate (dkd), e expand (aa), o ortho (dad... de), g gyro, s snub (dg).
- `conway(notation='tI', relax=40)`: The polyhedron for a Conway notation string, as a closed mesh with polygon faces on about the unit sphere.
- `build(notation='tI', relax=40)`: The flat-shaded polyhedron the command line writes, each face coloured by its number of corners.
- `main(argv=None)`: Command line: write the polyhedron as .gltf or .obj and print a JSON summary.

## Complexity

O(size of the result) per operator, plus relax * faces.

## Outputs

- `.gltf`: the flat-shaded polyhedron with COLOR_0 by face size (triangle, square, pentagon, hexagon)
- `.obj`: the same polyhedron as Wavefront OBJ

Axes and units: +Y up, metres.

## Open the result

- Blender: File > Import > glTF 2.0 and pick the `.gltf` file (Wavefront `.obj` imports through File > Import > Wavefront). Blender converts glTF +Y up to its own +Z up.
- Godot 4: copy the `.gltf` into the project folder and the editor imports it as a scene. At run time, `GLTFDocument.append_from_file(path, state)` followed by `generate_scene(state)` loads it without the editor.
- three.js: `new GLTFLoader().load("model.gltf", (gltf) => scene.add(gltf.scene))`; vertex colours show when the material has `vertexColors` set.

## Checks

`test_package.py` runs these cases and compares the results with known answers:

- `aaD`: `conway(notation="aaD", relax=10)` gives 60 vertices; 62 faces; watertight; Euler characteristic 2.
- `antiprism`: `conway(notation="A5", relax=0)` gives 10 vertices; 12 faces; watertight.
- `dkD`: `conway(notation="dkD", relax=10)` gives 60 vertices; 32 faces; watertight; Euler characteristic 2.
- `eC`: `conway(notation="eC", relax=10)` gives 24 vertices; 26 faces; watertight; Euler characteristic 2.
- `gC`: `conway(notation="gC", relax=10)` gives 38 vertices; 24 faces; watertight; Euler characteristic 2.
- `jC`: `conway(notation="jC", relax=10)` gives 14 vertices; 12 faces; watertight; Euler characteristic 2.
- `kT`: `conway(notation="kT", relax=10)` gives 8 vertices; 12 faces; watertight; Euler characteristic 2.
- `prism`: `conway(notation="P5", relax=0)` gives 10 vertices; 7 faces; watertight.
- `sC`: `conway(notation="sC", relax=10)` gives 24 vertices; 38 faces; watertight; Euler characteristic 2.
- `tI`: `conway(notation="tI", relax=10)` gives 60 vertices; 32 faces; watertight; Euler characteristic 2.

Each declared value, made wrong, must be refused, and a result with one element removed must fail the same case. The tests also check meshkit against a flipped face, an out-of-range index and a corrupted glTF, run the command line and verify the files it writes, and compare `example.gltf` with a fresh run.

## Limits

Geometry is approximate: new points start at centroids on the unit sphere and the relaxation only makes faces nearly planar; it does not produce canonical forms with equal edge lengths. Snub and gyro results are one of two mirror images.
