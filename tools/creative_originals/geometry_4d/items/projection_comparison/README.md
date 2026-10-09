# Perspective, stereographic and orthographic projections compared

`projection_comparison.py` projects one rotated 4D polytope three ways and writes the three wireframes side by
side in one glTF: perspective on the left, stereographic in the middle, orthographic on the right. It also
measures which properties each projection keeps. Input is a built-in polytope or any `fourd_polytope/v1` JSON
record (the other polytope tools in this family write them with `--out shape.json`).

## Mathematics

Perspective projection from the eye (0, 0, 0, d) onto w = 0 scales (x, y, z) by d/(d - w). It maps straight lines
to straight lines, but parallel edges converge, and it changes angles. Stereographic projection from the pole
(0, 0, 0, R) of the circumscribed 3-sphere scales by R/(R - w). It is conformal and maps circles on the sphere to
circles or lines, so each edge is drawn as its great-circle arc (the chord pushed out to the sphere), whose image
is a circular arc. Its derivative is dS(v) = R/(R - w) (v_xyz + v_w/(R - w) p_xyz), so tangent angles at a
vertex can be compared exactly: the largest error is below 1e-9 for the stereographic view and clearly non-zero
for the others. Orthographic projection drops w; it is linear, so parallel edges stay parallel, but lengths
shrink (the edges along w of the unrotated tesseract vanish).

## Run it

```
python projection_comparison.py --polytope tesseract --rotate xw=0.5,yz=0.35,zw=0.2 --out comparison.gltf
python projection_comparison.py --polytope 24cell --segments 4 --out 24cell_three_views.gltf
python projection_comparison.py --polytope my_polytope.json --out mine.gltf
```

```python
import projection_comparison as pc
shape = pc.make_polytope("tesseract")
errors = pc.angle_errors(shape["vertices"], shape["edges"], 2.0)
# {"perspective": ..., "stereographic": ~1e-16, "orthographic": ...}
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--polytope` | tesseract | `tesseract`, `16cell`, `24cell`, `5cell`, or a polytope JSON path. |
| `--rotate` | `xw=0.5,yz=0.35,zw=0.2` | Plane rotations applied left to right. |
| `--eye` | 2.5 | Perspective eye distance in circumradii. |
| `--gap` | 2.6 | Spacing of the three views, in circumradii. |
| `--radius` | 0.035 | Tube radius in circumradii. |
| `--sides` | 5 | Sides of each tube. |
| `--segments` | 6 | Segments per stereographic arc. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: three meshes named `perspective` (512 vertices), `stereographic` (2112 vertices, curved edges)
and `orthographic` (512 vertices), coloured by rotated w, at x = -2.6R, 0 and +2.6R. Each view is scaled so its
farthest vertex sits at the circumradius R, so the shapes compare at one size.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the materials for the depth colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Each view is rescaled to one size, which hides the real size differences between the projections.
Stereographic arcs are polylines of a few segments. Angle errors are measured at vertices only. The stereographic
view refuses a vertex at the pole, so choose a rotation that moves it. Input records should be convex polytopes
centred near the origin.
