# 24-cell from the Hurwitz quaternion units

`icositetrachoron_24cell.py` generates the 24-cell from two unit quaternions and writes it as a rotated,
projected wireframe (glTF) or as a polytope record (JSON). The vertices are coloured by which of three inscribed
16-cells they belong to.

## Mathematics

Read a point (x, y, z, w) as the quaternion w + xi + yj + zk. Multiplying the generators i and
(-1 + i + j + k)/2 together in every order closes after 24 elements: the binary tetrahedral group. These are the
unit Hurwitz integers: +-1, +-i, +-j, +-k and the 16 quaternions (+-1 +-i +-j +-k)/2. They are the vertices of
the 24-cell {3,4,3} with circumradius 1 and edge 1. The 24 octahedral cells face the directions
(+-1, +-1, 0, 0)/sqrt(2), which form a second 24-cell, so the polytope is self-dual. The quaternion group
Q8 = {+-1, +-i, +-j, +-k} has three cosets in the group; each coset is the vertex set of a 16-cell. Every edge of
the 24-cell joins two different cosets. With edge 1 the hypervolume is 2 and each octahedral cell has volume
sqrt(2)/3.

## Run it

```
python icositetrachoron_24cell.py --rotate xw=0.4,yz=0.25 --out 24cell.gltf
python icositetrachoron_24cell.py --style lines --project orthographic --out 24cell_lines.gltf
python icositetrachoron_24cell.py --out 24cell.json
```

```python
import icositetrachoron_24cell as c24
units = c24.hurwitz_units()          # 24 quaternions (a, b, c, d)
three = c24.cosets()                 # three lists of 8 quaternions
shape = c24.polytope()               # vertices, edges, faces, cells
c24.closure([(0, 1, 0, 0)])          # the cyclic group {1, i, -1, -i}
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--rotate` | `xw=0.4,yz=0.25` | Plane rotations applied left to right, radians or with a `deg` suffix. |
| `--project` | perspective | `perspective`, `stereographic` or `orthographic`. |
| `--eye` | 2.6 | Distance of the 4D eye from the centre (the circumradius is 1). |
| `--style` | tubes | `tubes` or `lines`. |
| `--radius` | 0.022 | Tube radius. |
| `--sides` | 8 | Sides of each tube. |
| `--out` | required | `.gltf` or `.json`. |

## Outputs

- `example.gltf`: the default command. One mesh, 1824 vertices, 2016 triangles, normals and per-vertex coset
  colours (COLOR_0).
- A `.json` `fourd_polytope/v1` record with 24 vertices, 96 edges, 96 triangular faces and 24 cells.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`. Set `vertex_color_use_as_albedo` on the material to see the coset colours.
- three.js: load it with `GLTFLoader` and add `gltf.scene` to the scene.

## Limits

Edges are drawn as straight tubes between projected vertices, so a stereographic image shows chords instead of
arcs. The group closure merges quaternions after rounding to 8 decimals; generators must be exact to that
precision. The perspective projection refuses an eye inside the rotated polytope.
