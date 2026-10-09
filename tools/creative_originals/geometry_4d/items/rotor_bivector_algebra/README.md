# Cl(4,0) rotors and bivector decomposition

`rotor_bivector_algebra.py` is a small geometric algebra for 4D space: multivectors, the geometric and outer
products, reversion, rotors and their action on vectors, reflections, and the split of any bivector into two
simple parts. The CLI writes the torus knot traced by a double rotation as a glTF tube inside a translucent
Clifford torus.

## Mathematics

A multivector holds 16 coefficients, one per basis blade, indexed by bitmask (e1 = x, e2 = y, e3 = z, e4 = w). The
product of blades a and b has mask a XOR b and the sign of the swaps that sort the factors; each e_i squares to +1,
so e12 squares to -1 and the pseudoscalar I = e1234 squares to +1. A bivector B gives the rotor R = exp(-B/2), and
v -> R v R~ rotates v; B = t e12 turns x toward y by t. B is simple (one plane) exactly when B ^ B = 0. Any 4D
bivector splits as B = B1 + B2 into commuting simple bivectors in orthogonal planes: with B^2 = S + q I, the
squared magnitudes alpha^2 and beta^2 solve t^2 + S t + (q/2)^2 = 0, and
B1 = B (alpha^2 + (q/2) I)/(alpha^2 - beta^2), B2 = B (beta^2 + (q/2) I)/(beta^2 - alpha^2). Then
exp(B) = (cos alpha + b1 sin alpha)(cos beta + b2 sin beta). With rates p and q in the xy and zw planes, the point
(1, 0, 1, 0)/sqrt(2) moves along a (p, q) torus knot on the Clifford torus. Its stereographic image for p = 2 and
q = 3 is a trefoil that winds twice around the z axis and links the unit circle three times (Gauss integral).

## Run it

```
python rotor_bivector_algebra.py --p 2 --q 3 --out trefoil.gltf
python rotor_bivector_algebra.py --p 3 --q 5 --shell off --samples 120 --out knot_3_5.gltf
```

```python
import rotor_bivector_algebra as ga
R = ga.rotor("xy=0.3,zw=1.1")
ga.sandwich(R, (1.0, 0.0, 0.0, 0.0))            # x turned 0.3 toward y
B = ga.bivector("xy=0.4,xz=-0.7,zw=-0.9")
B1, B2 = ga.split_bivector(B)                    # simple, commuting, B1 + B2 == B
ga.is_simple(ga.bivector("xy=1,xz=2"))           # True
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--p` | 2 | Rate in the xy plane (turns of the knot around one core circle). |
| `--q` | 3 | Rate in the zw plane. |
| `--samples` | 180 | Points along the knot. |
| `--sides` | 6 | Sides of the knot tube. |
| `--radius` | 0.06 | Tube radius. |
| `--shell` | on | Include the translucent Clifford torus. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: `torus_knot`, a tube of 2160 vertices coloured along the curve, and `clifford_torus`, a
translucent (alpha 0.22) torus of 720 vertices.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; enable `vertex_color_use_as_albedo` on the knot material for its colours.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Multivectors are dense lists of 16 floats and products loop over all blade pairs: fine for exploration and tests,
slow for bulk transforms. `exp_multivector` uses a truncated Taylor series after scaling and squaring. Isoclinic
bivectors have no unique split and are refused. The translucent torus relies on the viewer's alpha sorting.
