# Hopf fibration fibres as linked circles

`hopf_fibration.py` draws the Hopf fibration: the 3-sphere split into circles, one over each point of an ordinary
sphere. It lifts chosen base points to their circles, projects them into 3D, where every two circles link, and
writes them as coloured tubes next to a small base sphere whose dots carry the same colours.

## Mathematics

Read a point (x, y, z, w) of S^3 as the unit quaternion q = w + xi + yj + zk. The Hopf map h(q) = q i conj(q) is
the image of i under the rotation q, a point of S^2. Right multiplication by e^{it} does not change h, since
e^{it} fixes i under conjugation, so the fibre over a base point p is the great circle q(p) e^{it}, where q(p) is
any lift of p (here the shortest rotation from i to p). The first coordinate of h(q) is
(w^2 + x^2) - (y^2 + z^2), so the fibres over a circle of latitude around the x axis fill a torus, and over the
circle x = 0 they fill the Clifford torus w^2 + x^2 = y^2 + z^2 = 1/2. Any two fibres are Clifford parallel, at a
constant distance along their length, and they link once; stereographic projection maps them to circles in R^3
that keep these links. The fibre over (1, 0, 0) passes through the projection pole (0, 0, 0, 1), so the base
circles are taken around the x axis and stay away from it.

## Run it

```
python hopf_fibration.py --latitudes 100,130,155 --per-ring 8 --out hopf.gltf
python hopf_fibration.py --latitudes 90 --per-ring 8 --samples 24 --inset off --out clifford_fibres.gltf
```

```python
import hopf_fibration as hf
circle = hf.fibre((0.0, 1.0, 0.0), samples=48)      # 4D points of one fibre
hf.hopf_map(hf.fourd.point_to_quaternion(circle[5]))  # (0, 1, 0)
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--latitudes` | 100,130,155 | Base circles, as angles in degrees from the x axis (strictly between 0 and 180). |
| `--per-ring` | 8 | Fibres per base circle; alternate circles are offset by half a step. |
| `--samples` | 30 | Points per fibre. |
| `--radius` | 0.04 | Tube radius. |
| `--sides` | 4 | Sides of each tube. |
| `--inset` | on | Draw the base sphere with dots in the fibre colours. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: `hopf_fibres` (24 closed tubes over three base circles, 2880 vertices, one colour per fibre),
`base_sphere` (a translucent sphere) and `base_points` (24 dots in the fibre colours) placed to the right.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the materials for the fibre colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Fibres are polygons of the given sample count. Base circles must avoid the x axis direction, whose fibre passes
through the projection pole; fibres near it become very large. The inset sphere uses alpha blending.
