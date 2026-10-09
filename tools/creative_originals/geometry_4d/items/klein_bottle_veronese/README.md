# Klein bottle and Veronese surface embedded in 4D

`klein_bottle_veronese.py` builds two surfaces that cannot sit in 3D space without crossing themselves but fit
in 4D cleanly: the Klein bottle and the real projective plane (the Veronese surface). It checks their topology on
their meshes and writes their 3D shadows side by side, coloured by the coordinate that was dropped, so the two
sheets that cross in 3D show different colours.

## Mathematics

The Klein bottle is K(u, v) = ((R + r cos v) cos u, (R + r cos v) sin u, r sin v cos(u/2), r sin v sin(u/2)).
Going once around u flips (z, w), which is the same point as v -> -v, so the grid closes with the identification
(u + 2 pi, v) ~ (u, -v). Dropping w gives the familiar 3D Klein bottle, which crosses itself along u = pi where the
two sheets differ only in w. The Veronese map (x, y, z) -> (xy, xz, yz, (x^2 - y^2)/2) sends antipodal points of
the sphere to the same place and is otherwise injective, so it embeds the projective plane. Dropping its last
coordinate gives Steiner's Roman surface X^2 Y^2 + Y^2 Z^2 + Z^2 X^2 = X Y Z (for unit (x, y, z) both sides equal
x^2 y^2 z^2), which crosses itself. On the quotient meshes, V - E + F is 0 for the Klein bottle and 1 for the
projective plane, and propagating a triangle orientation across shared edges always meets a conflict: both are
non-orientable. A torus mesh, used as a control, passes the same propagation.

## Run it

```
python klein_bottle_veronese.py --out klein_and_roman.gltf
python klein_bottle_veronese.py --columns 16 --rows 8 --subdivisions 2 --out coarse_surfaces.gltf
```

```python
import klein_bottle_veronese as kv
points, triangles = kv.klein_mesh(24, 12)
kv.euler_characteristic(points, triangles)      # 0
kv.is_orientable(triangles)                     # False
kv.closest_far_pair(points, triangles, 4)       # clearly above 0: embedded in R^4
kv.closest_far_pair(points, triangles, 3)       # 0: the 3D shadow crosses itself
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--columns` | 32 | Klein bottle grid steps along u (even). |
| `--rows` | 12 | Klein bottle grid steps along v. |
| `--subdivisions` | 3 | Icosphere subdivisions for the Veronese surface (0 to 4). |
| `--gap` | 2.6 | Distance between the two models. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: `klein_bottle_shadow` (768 flat triangles, 2304 vertices) on the left and `roman_surface_shadow`
(640 flat triangles, 1920 vertices) on the right, each scaled to radius 1 and coloured from blue to amber by the
dropped coordinate. Materials are double-sided.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the materials for the colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Meshes are flat-shaded with duplicated vertices, since a non-orientable surface has no consistent normal field.
The embedding check is the smallest distance between mesh vertices more than three edges apart, a sampled test,
not a proof. The colour scale is set per surface.
