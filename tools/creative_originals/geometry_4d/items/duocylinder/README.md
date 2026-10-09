# Duocylinder measures and diagonal slices

`duocylinder.py` works with the duocylinder, the 4D product of two disks. It gives its hypervolume, boundary and
ridge measures, confirms them by adding up slices, and writes the sweep of its diagonal slices as a glTF animation:
a lens that grows into a Steinmetz bicylinder (the solid two crossing cylinders share) and shrinks again.

## Mathematics

The duocylinder is {x^2 + y^2 <= r1^2, z^2 + w^2 <= r2^2}, with hypervolume pi^2 r1^2 r2^2. Its boundary is two
solid tori, a circle of length 2 pi r1 times a disk of area pi r2^2 and the reverse, so the boundary 3-volume is
2 pi^2 r1 r2 (r1 + r2); the two meet on a flat ridge torus of area 4 pi^2 r1 r2. A slice w = c is a solid cylinder
of volume pi r1^2 * 2 sqrt(r2^2 - c^2), and integrating over c gives pi^2 r1^2 r2^2 again (Cavalieri). For the
unit duocylinder, the slice x + z = k is {x^2 + y^2 <= 1, (k - x)^2 + w^2 <= 1}: two unit cylinders with
perpendicular axes k apart. At k = 0 it is the Steinmetz bicylinder of volume 16/3, stretched by sqrt(2) along the
slice's first axis, so 16 sqrt(2)/3 in the slice. Integrating the diagonal slice volumes over the offset k/sqrt(2)
gives pi^2 as well. Each cylinder face of the slice is straight along w (or y), so four ruled strips over a
Chebyshev grid in x mesh it with exact edges, with the same topology for every k.

## Run it

```
python duocylinder.py --frames 12 --out duocylinder_sweep.gltf
python duocylinder.py --frames 4 --segments 8 --reach 1.5 --out duocylinder_coarse.gltf
```

```python
import duocylinder as dc
dc.hypervolume()                 # pi^2
dc.cavalieri_diagonal()          # pi^2 from the diagonal slices
dc.diagonal_slice_volume(0.0)    # 16 sqrt(2)/3
positions, indices = dc.diagonal_slice(0.8)
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--frames` | 12 | Keyframes of the sweep from -reach to +reach. |
| `--segments` | 24 | Grid steps along x on each of the four strips. |
| `--reach` | 1.85 | Largest |k| of the slice x + z = k (the slice vanishes at 2). |
| `--duration` | 6 | Seconds for the sweep. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf`: one mesh of 200 vertices and 192 triangles, coloured per strip (warm for the cylinder around the w
axis, cool for the one around the y axis), 11 morph targets with normals and one animation `diagonal_sweep` of 6 s.

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0, then play the timeline.
- Godot 4: play the `diagonal_sweep` animation of the AnimationPlayer; enable `vertex_color_use_as_albedo` on the
  material for the strip colours.
- three.js: load with `GLTFLoader`, then `new THREE.AnimationMixer(gltf.scene).clipAction(gltf.animations[0]).play()`.

## Limits

The sweep and the diagonal formulas are for the unit duocylinder; the measure functions take any radii. Slice
volumes use Simpson's rule after a cosine substitution. Keyframes are morph targets, so vertices move along chords
between them.
