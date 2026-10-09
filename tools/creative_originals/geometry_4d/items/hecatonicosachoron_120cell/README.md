# 120-cell from its seven coordinate classes

`hecatonicosachoron_120cell.py` builds the 120-cell, the largest regular 4-polytope, from an explicit coordinate
rule. It finds its 120 dodecahedral cells and 720 pentagons, splits the 600 vertices into five inscribed 600-cells,
and writes a glTF that shows two linked rings of ten cells, joined face to face, over all 1200 edges.

## Mathematics

With phi = (1 + sqrt 5)/2, the 600 vertices of circumradius 2 sqrt(2) are all permutations of (0, 0, +-2, +-2),
(+-1, +-1, +-1, +-sqrt 5), (+-phi^-2, +-phi, +-phi, +-phi) and (+-phi^-1, +-phi^-1, +-phi^-1, +-phi^2) (24 + 64 +
64 + 64), and the even permutations of (0, +-phi^-2, +-1, +-phi^2), (0, +-phi^-1, +-phi, +-sqrt 5) and
(+-phi^-1, +-1, +-phi, +-2) (96 + 96 + 192). The module scales them to circumradius 1. The cells face the 120
icosians: +-1, +-i, +-j, +-k, the 16 quaternions (+-1 +-i +-j +-k)/2 and the even permutations of
(+-phi, +-1, +-phi^-1, 0)/2. Each cell is the set of 20 vertices furthest along one icosian direction, each
pentagon is shared by two cells, and the result is {5,3,3} with V - E + F - C = 600 - 1200 + 720 - 120 = 0 and
hypervolume (15/4)(105 + 47 sqrt 5) a^4 for edge a. Left multiplication by an icosian permutes the vertices (read
as quaternions); the five orbits are five disjoint 600-cells. The cells centred at 1, q, q^2, ..., q^9 for the
order-10 icosian q = (phi, 1, phi^-1, 0)/2 form a closed ring in which neighbours share a pentagon. The cells
centred at k, kq, ..., kq^9 form a second ring in the absolutely orthogonal plane; the two rings link.

## Run it

```
python hecatonicosachoron_120cell.py --rotate xw=0.3,yz=0.15 --out 120cell.gltf
python hecatonicosachoron_120cell.py --project orthographic --shrink 0.8 --out 120cell_ortho.gltf
python hecatonicosachoron_120cell.py --out 120cell.json
```

```python
import hecatonicosachoron_120cell as h
shape = h.polytope()                  # 600 vertices, 1200 edges, 720 faces, 120 cells
five = h.inscribed_600cells()         # five lists of 120 vertex indices
ring = h.cell_ring()                  # ten cell indices
other = h.cell_ring((0, 0, 0, 1))     # the linked ring through the cell at k
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--rotate` | `xw=0.3,yz=0.15` | Plane rotations applied left to right. |
| `--project` | perspective | `perspective`, `stereographic` or `orthographic`. |
| `--eye` | 2.2 | 4D eye distance (circumradius 1). |
| `--shrink` | 0.94 | Scale of each ring cell toward its own centre. |
| `--edges` | plain | Edge colours: `plain`, or `orbits` for one colour per inscribed 600-cell. |
| `--out` | required | `.gltf` or `.json`. |

## Outputs

`example.gltf` holds `cell_ring` (two linked rings of ten flat-shaded dodecahedra in warm and cool colours, 1200
vertices, 720 triangles) and `edges` (600 vertices, 1200 grey lines, unlit).

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`. Enable `vertex_color_use_as_albedo` on the materials for the colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Edges are one-pixel lines whose width depends on the viewer; only the 20 ring cells are solid. Building the polytope
takes about half a second in CPython. Vertices are merged after rounding to 12 decimals and orbits after rounding to
7, which suits the built-in coordinates, not arbitrary input.
