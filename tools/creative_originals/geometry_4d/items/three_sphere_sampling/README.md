# Uniform point sets on the 3-sphere

`three_sphere_sampling.py` makes evenly spread sets of unit quaternions (points of the 3-sphere S^3) in three
ways, measures how well each covers the sphere, and writes a set as a glTF point cloud through stereographic
projection. Uses include rotation sampling for search, orientation grids, and 4D particle placement.

## Mathematics

Normalizing four independent normal numbers gives uniform random points, since the normal law is rotationally
symmetric. The Hopf grid uses the Hopf map q -> q i conj(q) from S^3 to S^2: it maps every great circle
q(p) e^{it} to one base point p, and because the fibres all have length 2 pi, a uniform set on S^2 (a Fibonacci
spiral) times evenly spaced fibre points is uniform on S^3. The super-Fibonacci spiral sets s = k + 1/2,
r = sqrt(s/n), R = sqrt(1 - s/n), a = 2 pi s/sqrt(2), b = 2 pi s/psi with psi^4 = psi + 4, and
q_k = (r sin a, r cos a, R sin b, R cos b); r^2 is uniform on [0, 1], as for uniform points, and the two irrational
turn rates spread the angles. A cap of angular radius theta holds the fraction (theta - sin(theta) cos(theta))/pi
of the volume of S^3; comparing point counts in caps with that value gives the cap discrepancy. The package tests
check that the spiral's smallest gap is more than three times that of random points and that its discrepancy is
under 0.02 for 600 points.

## Run it

```
python three_sphere_sampling.py --method super_fibonacci --count 2000 --out s3_points.gltf
python three_sphere_sampling.py --method hopf_grid --count 600 --out hopf_grid.gltf
```

```python
import three_sphere_sampling as s3
points = s3.super_fibonacci(1000)       # unit quaternions (x, y, z, w)
s3.separation(points), s3.cap_discrepancy(points)
s3.hopf_map(points[0])                  # its base point on S^2
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--method` | super_fibonacci | `gaussian`, `hopf_grid` or `super_fibonacci`. |
| `--count` | 2000 | Number of points. |
| `--clip` | 3 | Leave out points whose stereographic image lies beyond this radius. |
| `--seed` | 1 | Seed of the `gaussian` sampler. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: 2000 super-Fibonacci points projected stereographically from (0, 0, 0, 1); 104 near the pole are
clipped, leaving one POINTS mesh of 1896 vertices coloured by w (unlit).

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0.
- Godot 4: copy the file into the project, or load it at run time with `GLTFDocument.append_from_file` and
  `generate_scene`; set `use_point_size` and `vertex_color_use_as_albedo` on the material for visible coloured points.
- three.js: load with `GLTFLoader` and add `gltf.scene`.

## Limits

Separation is an O(n^2) scan; covering radius and discrepancy are estimates from random probes and caps, so they
suit a few thousand points. The Hopf grid rounds the count to bases times fibre points. Points near the projection
pole are clipped from the glTF. POINTS render at one pixel in most viewers.
