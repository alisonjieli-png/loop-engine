# 16-cell from signed axes

`cross_polytope_16cell.py` builds the 16-cell (the 4D cross-polytope) with exact combinatorics and writes it as
16 exploded tetrahedral cells, a tube wireframe or LINES (glTF), or as a polytope record (JSON).

## Mathematics

The vertices are +-r on each of the four axes. Every two vertices that are not opposite share an edge (24). A
triangular face uses three different axes and one sign on each (4 x 8 = 32). A tetrahedral cell picks one sign on
every axis, so the 16 cells are the 16 sign vectors. The symbol is {3,3,4}, V - E + F - C = 8 - 24 + 32 - 16 = 0,
and with circumradius 1 the edge is sqrt(2) and the hypervolume 2/3. The edge graph is the cocktail party graph
K_{2,2,2,2}: each vertex is joined to all others except its opposite. The centres of the tesseract's eight cubic
cells are exactly the 16-cell vertices, so the two polytopes are dual. The 8 cells around +w form one half of a
bipyramid over the octahedron of the other six vertices.

## Run it

```
python cross_polytope_16cell.py --style cells --rotate xw=0.3,zw=0.2,yz=0.5 --out 16cell.gltf
python cross_polytope_16cell.py --style tubes --out 16cell_tubes.gltf
python cross_polytope_16cell.py --out 16cell.json
```

```python
import cross_polytope_16cell as c16
shape = c16.polytope(radius=1.0)
c16.is_cocktail_party(shape["edges"])     # True
c16.apex_cells(shape, 6)                  # the 8 cells around +w
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--radius` | 1 | Circumradius. |
| `--rotate` | `xw=0.3,zw=0.2,yz=0.5` | Plane rotations applied left to right. |
| `--project` | perspective | `perspective`, `stereographic` or `orthographic`. |
| `--eye` | 2.6 | 4D eye distance in circumradii. |
| `--style` | cells | `cells`, `tubes` or `lines`. |
| `--tube` | 0.025 | Tube radius in circumradii. |
| `--shrink` | 0.6 | Scale of each cell toward its own centre. |
| `--cells` | front | For `cells`: only the cells facing the 4D eye (they tile the projected outline without overlap), or `all`. |
| `--out` | required | `.gltf` or `.json`. |

## Outputs

`example.gltf`: the 8 tetrahedra that face the 4D eye (the cells around one vertex), one colour per sign vector,
96 vertices and 32 triangles.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the material for the cell colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

The exploded view shrinks each projected cell toward its own projected centre; this is a display choice. Under the
stereographic projection the flat faces approximate curved cell images. The perspective projection refuses an eye
inside the rotated 16-cell.
