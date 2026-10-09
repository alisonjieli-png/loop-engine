# Duoprisms as products of two polygons

`duoprism.py` builds the {p}x{q} duoprism, the product of a p-gon and a q-gon, for any p and q from 3 up. It
writes exploded prism cells, a tube wireframe or LINES (glTF), or a polytope record (JSON).

## Mathematics

Put a p-gon of radius r1 in the xy plane and a q-gon of radius r2 in the zw plane. Vertex (i, j) is
(r1 cos 2 pi i/p, r1 sin 2 pi i/p, r2 cos 2 pi j/q, r2 sin 2 pi j/q). An edge changes i or j by one, a square face
changes both, and the p q-gons and q p-gons complete the faces. The cells form two linked rings: p q-gonal prisms
and q p-gonal prisms. So V = pq, E = 2pq, F = pq + p + q and C = p + q, and V - E + F - C = 0 for every p and q.
With r = 1/(2 sin(pi/n)) all edges have length 1. The hypervolume is the product of the two polygon areas
(n/2) r^2 sin(2 pi/n). With equal radii every vertex lies on one Clifford torus. The unit-edge {4}x{4}, turned 45
degrees in the xy and zw planes, is the tesseract {+-1/2}^4.

## Run it

```
python duoprism.py --p 5 --q 7 --style cells --out duoprism_5_7.gltf
python duoprism.py --p 3 --q 12 --radii equal --style tubes --out duoprism_3_12.gltf
python duoprism.py --p 6 --q 6 --out duoprism_6_6.json
```

```python
import duoprism
shape = duoprism.polytope(3, 8)
duoprism.expected_counts(3, 8)      # (24, 48, 35, 11)
duoprism.is_uniform(shape)          # True
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--p` | 5 | Sides of the polygon in the xy plane. |
| `--q` | 7 | Sides of the polygon in the zw plane. |
| `--radii` | uniform | `uniform` (unit edges) or `equal` (both radii 1). |
| `--rotate` | `xw=0.5,yz=0.3` | Plane rotations applied left to right. |
| `--project` | perspective | `perspective`, `stereographic` or `orthographic`. |
| `--eye` | 2.6 | 4D eye distance in circumradii. |
| `--style` | cells | `cells`, `tubes` or `lines`. |
| `--shrink` | 0.86 | Scale of each prism toward its own centre. |
| `--tube` | 0.025 | Tube radius in circumradii. |
| `--cells` | front | For `cells`: only the prisms facing the 4D eye (they tile the projected outline without overlap), or `all`. |
| `--out` | required | `.gltf` or `.json`. |

## Outputs

`example.gltf`: the {5}x{7} duoprism; the 5 prisms that face the 4D eye, heptagonal prisms in warm colours and
pentagonal prisms in cool colours; 174 vertices and 96 triangles.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the material for the colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

The CLI caps p times q at 4096. The exploded view shrinks each projected prism toward its own projected centre, a
display choice. The perspective projection refuses an eye inside the rotated duoprism, and flat faces under the
stereographic projection approximate curved cell images.
