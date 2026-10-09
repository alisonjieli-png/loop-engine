# Tesseract from 4-bit vertex labels

`tesseract.py` builds the tesseract (the 4D hypercube, or 8-cell) with exact combinatorics, rotates it in 4D,
projects it to 3D and writes a tube wireframe as glTF, or the full polytope as JSON. It also gives the Gray code
cycle through all 16 vertices and the two 16-cells inscribed in the tesseract.

## Mathematics

Label the 16 vertices 0 to 15. Bit i of the label picks the sign of coordinate i, so vertex k sits at
(size/2)(2 b_i - 1). Two vertices share an edge when their labels differ in exactly one bit (32 edges). A square
face frees two bits and fixes the other two (6 axis pairs times 4 settings, 24 faces). A cubic cell fixes one bit
(4 axes times 2 values, 8 cells). The Schlafli symbol is {4,3,3}, V - E + F - C = 16 - 32 + 24 - 8 = 0, and with
edge 2 the hypervolume is 16 and the surface 3-volume is 64. The reflected Gray code k XOR (k >> 1) visits every
vertex once along edges. The labels of even bit parity, and those of odd parity, each form a 16-cell.

## Run it

```
python tesseract.py --rotate xw=0.6,yz=0.3 --project perspective --out tesseract.gltf
python tesseract.py --style lines --project stereographic --out tesseract_lines.gltf
python tesseract.py --out tesseract.json
```

```python
import tesseract
shape = tesseract.polytope()           # {"vertices", "edges", "faces", "cells"}
cycle = tesseract.gray_cycle()         # [0, 1, 3, 2, 6, ...]
even, odd = tesseract.half_tesseracts()
mesh = tesseract.wireframe(rotation="xy=0.2,zw=0.9")
```

`fourd.py` (shipped beside it) must be importable from the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--size` | 2 | Edge length. |
| `--rotate` | `xw=0.6,yz=0.3` | Plane rotations applied left to right. Planes: xy, xz, xw, yz, yw, zw. Angles in radians, or with a `deg` suffix. |
| `--project` | perspective | `perspective` (eye on the w axis), `stereographic` (from the pole of the circumscribed 3-sphere) or `orthographic` (drop w). |
| `--eye` | 2.5 | Distance of the 4D eye from the centre, in circumradii. |
| `--style` | tubes | `tubes` for a lit mesh, `lines` for a LINES primitive. |
| `--radius` | 0.035 x size | Tube radius. Vertex spheres are 1.9 times larger. |
| `--sides` | 8 | Sides of each tube. |
| `--out` | required | `.gltf` writes the wireframe, `.json` the `fourd_polytope/v1` record. |

## Outputs

- `example.gltf`: the default command. One mesh of 704 vertices and 832 triangles, normals, and vertex colours
  (COLOR_0) that run from blue to amber along the rotated w axis.
- A `.json` record with `vertices`, `edges`, `faces` (vertex cycles) and `cells` (face indices).

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0, then pick the file.
- Godot 4: put the file in the project folder and the editor imports it as a scene. At run time,
  `GLTFDocument.append_from_file` with a `GLTFState`, then `generate_scene`, loads it. Godot does not use the
  vertex colours until `vertex_color_use_as_albedo` is set on the material.
- three.js: `new GLTFLoader().load("tesseract.gltf", (gltf) => scene.add(gltf.scene))`.

## Limits

Tubes are straight segments between projected vertices. Under the stereographic projection they are chords, not
the circular arcs that are the true images of the edges. The perspective projection refuses an eye inside the
rotated object. The depth colour is a linear map of w and is not physically based.
