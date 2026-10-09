# 4D rotation exponential, logarithm and geodesics

`rotation_exp_log.py` converts between 4D rotation matrices and their generators. It builds a rotation from rates
in the six coordinate planes, recovers the two plane angles and the generator of any rotation, names the kind of
rotation, interpolates between two orientations along the shortest path, and writes a looping glTF of a
tesseract or 24-cell turning under a fixed generator.

## Mathematics

Every 4D rotation turns two absolutely orthogonal planes by angles alpha and beta. Its generator is a 4x4
skew-symmetric matrix A. The invariants a^2 + b^2 = -tr(A^2)/2 and ab = Pf(A) = A01 A23 - A02 A13 + A03 A12 give
the two rates, and A^4 + (a^2 + b^2) A^2 + a^2 b^2 = 0, so exp(A) is a cubic in A:
exp(A) = c0 + c1 A + c2 A^2 + c3 A^3 with c0 = (a^2 cos b - b^2 cos a)/(a^2 - b^2),
c1 = (a^2 sin(b)/b - b^2 sin(a)/a)/(a^2 - b^2), c2 = (cos b - cos a)/(a^2 - b^2) and
c3 = (sin(b)/b - sin(a)/a)/(a^2 - b^2); when a = b the result is cos(a) + A sin(a)/a. For the logarithm, tr(R)
and tr(R^2) give cos(alpha) and cos(beta), the skew part K = (R - R^T)/2 gives their sines, and atan2 gives each
angle. The symmetric part (R + R^T)/2 splits into the projectors of the two planes, and K times each projector
divided by sin(angle) is that plane's unit generator. A rotation is simple when one angle is 0, isoclinic when the
angles are equal (for example quaternion multiplication), double otherwise. The geodesic from R0 to R1 is
R0 exp(t log(R0^T R1)).

## Run it

```
python rotation_exp_log.py --rates xw=1,yz=2 --polytope tesseract --out tesseract_loop.gltf
python rotation_exp_log.py --rates xy=1,zw=1 --polytope 24cell --frames 24 --out 24cell_isoclinic.gltf
```

```python
import rotation_exp_log as rel
R = rel.expm(rel.generator("xy=0.3,zw=1.1"))
rel.rotation_angles(R)            # (1.1, 0.3)
rel.classify(R)                   # "double"
A = rel.logm(R)                   # skew matrix with expm(A) == R
half = rel.geodesic(rel.fourd.identity(4), R, 0.5)
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--rates` | `xw=1,yz=2` | Plane rates of the generator A. Integer rates make the loop close after 2 pi. |
| `--polytope` | tesseract | `tesseract` or `24cell`. |
| `--frames` | 48 | Keyframes over t in [0, 2 pi] (the last equals the first for integer rates). |
| `--style` | tubes | Unlit three-sided `tubes` or a `lines` primitive. |
| `--radius` | 0.025 | Tube radius in circumradii. |
| `--eye` | 2.5 | 4D eye distance in circumradii (perspective). |
| `--duration` | 8 | Seconds per loop. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: the tesseract as one mesh of unlit three-sided tubes (192 vertices, colours by starting w), 48
morph targets and one animation `rotation_loop` of 8 s that turns it by exp(t A) with rates 1 and 2 in the xw and
yz planes.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0, then play the timeline.
- Godot 4: the morph targets load as blend shapes with one animation track each; play the `rotation_loop`
  animation of the AnimationPlayer. At run time, `GLTFDocument.append_from_file` and `generate_scene` give the
  same nodes.
- three.js: load with `GLTFLoader`, then `new THREE.AnimationMixer(gltf.scene).clipAction(gltf.animations[0]).play()`.

## Limits

Keyframes are morph targets, so vertices move along chords between keyframes; the largest deviation from the true
rotation is 1 - cos(step/2) of the radius (0.0086 for the example). Tube normals are not morphed, so the tubes
use an unlit material. The logarithm is ill-conditioned for nearly isoclinic rotations, whose invariant planes
are not unique, and picks one plane pair for rotations by pi.
