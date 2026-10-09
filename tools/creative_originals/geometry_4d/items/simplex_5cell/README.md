# 5-cell from the standard simplex of R5

`simplex_5cell.py` builds the regular 5-cell (the 4-simplex) and writes it as an exploded set of five
tetrahedral cells, a tube wireframe or LINES (glTF), or as a polytope record (JSON). It also gives barycentric
coordinates, an inside test and uniform random points inside the simplex.

## Mathematics

The unit vectors e_1 to e_5 of R^5 are five points at equal distance sqrt(2) from each other, lying in the
hyperplane where the coordinates sum to 1. The Helmert vectors h_k = (1, ..., 1, -k, 0, ...)/sqrt(k(k+1)) for
k = 1..4 are orthonormal and span the parallel hyperplane through the origin, so (e_i . h_1, ..., e_i . h_4) are
coordinates of a regular simplex in R^4 centred at the origin. All 10 pairs are edges, all 10 triples are faces
and all 5 quadruples are cells: {3,3,3}, V - E + F - C = 0. With edge 1 the circumradius is sqrt(2/5), the
hypervolume is sqrt(5)/96 and the dihedral angle is arccos(1/4), about 75.52 degrees. Every permutation of the 5
vertices preserves all distances (120 symmetries). Barycentric weights come from solving the affine map of the
simplex; a point is inside when all five are non-negative. Sorted uniform numbers give Dirichlet(1, ..., 1)
weights, which are uniform inside the simplex.

## Run it

```
python simplex_5cell.py --style cells --rotate xw=3.0,yz=0.4 --out 5cell.gltf
python simplex_5cell.py --style tubes --project orthographic --out 5cell_tubes.gltf
python simplex_5cell.py --out 5cell.json
```

```python
import simplex_5cell as s5
s5.barycentric((0.0, 0.0, 0.0, 0.0))     # (0.2, 0.2, 0.2, 0.2, 0.2)
points = s5.sample_points(1000, seed=7)
s5.contains(points[0])                   # True
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--edge` | 1 | Edge length. |
| `--rotate` | `xw=3.0,yz=0.4` | Plane rotations applied left to right, radians or with a `deg` suffix. |
| `--project` | perspective | `perspective`, `stereographic` or `orthographic`. |
| `--eye` | 3 | 4D eye distance in circumradii. |
| `--style` | cells | `cells` (each tetrahedron shrunk toward its centre), `tubes` or `lines`. |
| `--radius` | 0.03 x edge | Tube radius for `tubes`. |
| `--shrink` | 0.62 | Scale of each cell toward its own centre for `cells`. |
| `--cells` | front | For `cells`: only the cells facing the 4D eye (they tile the projected outline without overlap), or `all`. |
| `--out` | required | `.gltf` or `.json`. |

## Outputs

`example.gltf` is the default command, seen nearly vertex first: the four tetrahedra that face the 4D eye, each
shrunk toward its centre in its own colour, 48 vertices and 16 triangles. The `.json` record lists vertices, edges, faces and cells.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`. Enable `vertex_color_use_as_albedo` on the material to see the cell colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

The exploded view shrinks each projected cell toward its own projected centre; this is a display choice, not a 4D
operation. Sampling uses Python's `random` with a fixed seed. Under the stereographic projection the flat faces
only approximate the curved images of the cells.
