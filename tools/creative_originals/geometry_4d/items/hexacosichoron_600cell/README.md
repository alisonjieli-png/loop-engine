# 600-cell from the binary icosahedral group

`hexacosichoron_600cell.py` generates the 600-cell from two unit quaternions, builds its edges, faces and cells,
and splits it into Hopf fibres and inscribed 24-cells. It writes a glTF in which the 12 Hopf decagons are coloured
tubes and all 720 edges are lines, or a polytope record (JSON).

## Mathematics

A point (x, y, z, w) is the quaternion w + xi + yj + zk. The quaternions s = (1 + i + j + k)/2 and
t = (phi + i/phi + j)/2, with phi the golden ratio, satisfy s^3 = t^5 = (st)^2 = -1. Multiplying them in every
order closes after 120 elements, the binary icosahedral group: the vertices of the 600-cell {3,3,5} with
circumradius 1 and edge 1/phi. Each vertex has 12 neighbours. The triangles and tetrahedra of the edge graph are
the 1200 faces and 600 cells (V - E + F - C = 0); the hypervolume is (25/4)(2 + sqrt(5)) a^4 for edge a. The
powers of t form a cyclic subgroup of order 10. Its 12 left cosets g, gt, gt^2, ... are regular decagons on great
circles, and these circles are fibres of a Hopf fibration (pairwise Clifford parallel). The 24 Hurwitz units form
the binary tetrahedral subgroup; its 5 left cosets are five disjoint 24-cells inscribed in the 600-cell.

## Run it

```
python hexacosichoron_600cell.py --rotate xw=0.35,yz=0.2 --out 600cell.gltf
python hexacosichoron_600cell.py --project orthographic --radius 0.01 --out 600cell_ortho.gltf
python hexacosichoron_600cell.py --out 600cell.json
```

```python
import hexacosichoron_600cell as h
group = h.icosians()                 # 120 quaternions
rings = h.hopf_decagons()            # 12 lists of 10, in order around each circle
inscribed = h.left_cosets(h.hurwitz_subgroup())   # 5 lists of 24
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--rotate` | `xw=0.35,yz=0.2` | Plane rotations applied left to right. |
| `--project` | perspective | `perspective`, `stereographic` or `orthographic`. |
| `--eye` | 2.4 | 4D eye distance (circumradius 1). |
| `--radius` | 0.012 | Radius of the decagon tubes. |
| `--sides` | 6 | Sides of each tube. |
| `--out` | required | `.gltf` or `.json`. |

## Outputs

`example.gltf` holds two meshes: `hopf_decagons` (2880 vertices, 3840 triangles, one colour per decagon) and
`edges` (120 vertices, 720 lines, unlit material through `KHR_materials_unlit`).

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`. Enable `vertex_color_use_as_albedo` on the decagon material for the fibre colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Only the decagon edges are tubes; the other edges are one-pixel lines whose width depends on the viewer. The
quaternion 1 is a vertex at the stereographic pole, so a stereographic image needs a rotation that moves it (the
default rotation does). Group closure merges elements after rounding to 8 decimals.
