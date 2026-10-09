# Coxeter plane projections of 4-polytopes

`coxeter_plane_projection.py` draws a 4D polytope in its most symmetric 2D view, the Coxeter plane. It writes an
SVG drawing or a flat glTF (edges and vertex dots in the xy plane). It works for the six regular 4-polytopes and
for any Wythoff polytope given as a Coxeter group and a ringing.

## Mathematics

Multiply the four simple reflections of a Coxeter group in node order. The product c, the Coxeter element, is a
rotation of order h, the Coxeter number: 5 for A4, 8 for B4, 12 for F4 and 30 for H4. In one of its two invariant
planes c turns by 2 pi/h. That plane is the eigenspace of the symmetric matrix (c + c^T)/2 for the eigenvalue
cos(2 pi/h), computed here as a null space. Projecting the vertices orthogonally onto it puts them on rings of h
points with h-fold rotational symmetry, and the outer ring traces the Petrie polygon. The tesseract shows two
octagons, the 24-cell two 12-gons, the 600-cell four rings of 30, and the 120-cell 600 points in 20 orbits of 30
(on 12 distinct radii).

## Run it

```
python coxeter_plane_projection.py --polytope 600cell --out coxeter_600cell.svg
python coxeter_plane_projection.py --polytope 120cell --out coxeter_120cell.gltf
python coxeter_plane_projection.py --group B4 --rings 1100 --out truncated_tesseract_coxeter.svg
```

```python
import coxeter_plane_projection as cp
group, vertices, edges = cp.named_polytope("24cell")
points = cp.project(group, vertices)
cp.rings(points)                 # [(radius, 12), (radius, 12)]
cp.element_order(cp.coxeter_element("H4"))   # 30
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--polytope` | 600cell | `5cell`, `tesseract`, `16cell`, `24cell`, `600cell` or `120cell`. |
| `--group` | none | Coxeter group (`A4`, `B4`, `D4`, `F4`, `H4`) for a Wythoff ringing; use with `--rings`. |
| `--rings` | none | Ringing such as `1100`, node 0 first. |
| `--style` | lines | glTF edges as `lines` or thin `tubes`. |
| `--out` | required | `.svg` or `.gltf`. |

## Outputs

- `example.svg`: the 600-cell, 120 vertices and 720 edges coloured from the centre (blue) to the rim (amber) on a
  dark background, 640 x 640.
- `example.gltf`: the same drawing in the glTF xy plane: `edges` (LINES, 120 vertices, 720 lines, unlit) and
  `vertices` (120 small spheres, 1440 vertices).

## Open the files

- SVG: any browser or vector editor.
- Blender 2.80 or later: File > Import > glTF 2.0; the drawing lies in the xy plane.
- Godot 4: copy the glTF into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the materials for the ring colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Orbits are capped at 3000 vertices. Edges join vertices at distance 1, the edge length of every Wythoff polytope.
Rings are grouped by radius, so two orbits at one radius count as one ring of 2h. The view is orthographic, and for
some ringings distinct vertices land on the same point.
