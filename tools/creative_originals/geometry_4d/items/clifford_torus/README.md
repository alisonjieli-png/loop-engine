# Clifford torus in the 3-sphere

`clifford_torus.py` works with the Clifford torus, the flat torus that sits inside the unit 3-sphere. It checks
the torus's geometry with exact answers and writes a glTF in which its stereographic image turns through 4D in a
seamless loop, changing between doughnut shapes along the way.

## Mathematics

The torus is (cos u, sin u, cos v, sin v)/sqrt(2). Its two tangent vectors are orthogonal with squared length 1/2,
so the induced metric is (du^2 + dv^2)/2: it is flat, with area (2 pi)^2/2 = 2 pi^2. In Hopf coordinates
(cos(eta) e^{ia}, sin(eta) e^{ib}) the volume element of S^3 is sin(eta) cos(eta) da db deta, and the torus is
eta = pi/4, so it splits the sphere into two solid tori of volume pi^2 each. Its core circles z = w = 0 and
x = y = 0 link once (Gauss integral after projecting from a pole on neither circle). Stereographic projection from
(0, 0, 0, 1) maps it to a torus of revolution with major radius sqrt(2) and minor radius 1. Rotating in the xy
plane slides the torus along itself. Rotating in the xz or yz plane leaves w unchanged, so no point reaches the
pole; the image then passes through a loop of Dupin cyclides and returns after 2 pi.

## Run it

```
python clifford_torus.py --plane xz --frames 16 --out clifford_loop.gltf
python clifford_torus.py --plane yz --frames 6 --columns 12 --rows 6 --out clifford_yz.gltf
```

```python
import clifford_torus as ct
ct.area()                  # 19.739... = 2 pi^2
ct.solid_torus_volumes()   # (pi^2, pi^2)
ct.image_radii()           # (1.41421..., 1.0)
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--plane` | xz | Rotation plane: `xy` (slides along itself), `xz` or `yz` (changes the image). |
| `--frames` | 16 | Keyframes per loop. |
| `--columns` | 24 | Grid steps along u. |
| `--rows` | 10 | Grid steps along v. |
| `--duration` | 8 | Seconds per loop. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: one mesh of 240 vertices and 480 triangles with 16 morph targets (positions and normals) and one
animation `rotate_xz` of 8 s. Vertex colours run around u and are banded along v, so the motion of the surface is
visible.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0, then play the timeline.
- Godot 4: play the `rotate_xz` animation of the AnimationPlayer; enable `vertex_color_use_as_albedo` on the
  material for the colours.
- three.js: load with `GLTFLoader`, then `new THREE.AnimationMixer(gltf.scene).clipAction(gltf.animations[0]).play()`.

## Limits

Keyframes are morph targets, so between them vertices move along chords and the surface shrinks slightly.
Rotation planes containing w are refused because they carry points through the projection pole. The solid torus
volumes come from Simpson's rule, with an error near 1e-10.
