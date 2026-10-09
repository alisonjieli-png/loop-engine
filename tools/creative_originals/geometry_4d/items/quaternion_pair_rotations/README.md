# 4D rotations as pairs of unit quaternions

`quaternion_pair_rotations.py` represents a rotation of 4-space by two unit quaternions. It builds the matrix from
a pair, recovers the pair from any rotation matrix, reads the two plane angles and the kind of rotation, and
interpolates between orientations along the shortest path. The CLI writes two 16-cells, one turning by left
multiplication and one by right multiplication, as a looping glTF.

## Mathematics

Read a point as the quaternion p = w + xi + yj + zk. For unit quaternions l and r, p -> l p conj(r) is a rotation,
and every rotation arises from exactly two pairs, (l, r) and (-l, -r). To decompose R: R(1) = l conj(r), and for
x in {i, j, k}, R(x) conj(R(1)) = l x conj(l). These three images form a 3D rotation matrix of the imaginary
quaternions, from which l follows by Shepperd's method; then r = conj(R(1)) l. Write l = cos(a) + sin(a) u and
r = cos(b) + sin(b) v. The two plane angles are a + b and |a - b|. When r = 1 every vector turns by a (a
left-isoclinic rotation); when l = 1 it is right-isoclinic; when a = b it is a simple rotation, and l = r is the
3D rotation that fixes the w axis. Left and right multiplications commute. The shortest path between two
rotations slerps both quaternions, using whichever lift of the end pair is closer.

## Run it

```
python quaternion_pair_rotations.py --angle-rate 1 --out isoclinic_pair.gltf
python quaternion_pair_rotations.py --angle-rate 2 --frames 16 --out isoclinic_fast.gltf
```

```python
import quaternion_pair_rotations as qp
R = qp.compose((0.6, 0.8, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))
qp.classify(*qp.decompose(R))      # "left_isoclinic"
qp.pair_angles(*qp.decompose(R))   # (0.927..., 0.927...)
mid = qp.interpolate(qp.fourd.identity(4), R, 0.5)
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--angle-rate` | 1 | Full isoclinic turns per loop. |
| `--frames` | 28 | Keyframes per loop. |
| `--style` | tubes | Unlit three-sided `tubes` or `lines`. |
| `--radius` | 0.03 | Tube radius (circumradius 1). |
| `--eye` | 2.6 | 4D eye distance (circumradius 1). |
| `--duration` | 6 | Seconds per loop. |
| `--gap` | 2.4 | Distance between the two models along x. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: two meshes of the 16-cell as unlit three-sided tubes (144 vertices each) placed side by side, 28
morph targets each, and one animation `isoclinic_loops` of 6 s: left multiplication by exp(t k) on the left model
and right multiplication on the right model.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0, then play the timeline.
- Godot 4: play the `isoclinic_loops` animation of the AnimationPlayer; the morph targets load as blend shapes.
- three.js: load with `GLTFLoader`, then `new THREE.AnimationMixer(gltf.scene).clipAction(gltf.animations[0]).play()`.

## Limits

Keyframes are morph targets, so vertices move along chords between them (at most 0.6 percent of the radius in
the example). Tube normals are not morphed, so the tubes use an unlit material. `decompose` returns the lift whose
left quaternion has a non-negative scalar part.
