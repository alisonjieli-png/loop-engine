# Exact hyperplane slice sweep as glTF morph targets

`slice_morph_animation.py` moves a hyperplane through a 4D polytope and writes the 3D cross-sections as one glTF
mesh with a morph-target animation. Playing the animation in a glTF viewer shows the exact slices, for example a
tesseract met corner first: a tetrahedron grows, its corners are cut into a truncated tetrahedron, it becomes an
octahedron at the centre, then the sequence reverses.

## Mathematics

The hyperplane is n . p = s. Each cell of the polytope is cut into tetrahedra coned from one of its vertices. For
one tetrahedron, sort its vertices by height h0 <= h1 <= h2 <= h3. Its slice is a triangle on (h0, h1), a
quadrilateral on (h1, h2) and a triangle on (h2, h3). One 4-gon covers all three: V1 runs along edge 02 and then
23, V2 along 03, V3 along 01 and then 13, and V4 along 01, 12 and then 23 (a triangle is a 4-gon with two equal
corners). Each corner is a linear function of s between consecutive vertex heights. So keyframes at the distinct
heights, with linear interpolation, give every intermediate slice exactly. The base mesh is the first keyframe,
morph target k is keyframe k minus the base, and the weights are one-hot per keyframe. When heights tie, a corner
may jump between two positions that coincide on screen; a second keyframe 1 ms later carries that jump. All slice
faces of one cell lie in one plane, so each keeps the cell's normal for the whole sweep. The package tests compare
the area and volume of the animated mesh with exact cross-sections inside every interval, for all four polytopes
and four directions; they agree to about 1e-15.

## Run it

```
python slice_morph_animation.py --polytope tesseract --direction vertex --out tesseract_slices.gltf
python slice_morph_animation.py --polytope tesseract --direction edge --out prisms.gltf
python slice_morph_animation.py --polytope 24cell --direction 1,2,3,4 --duration 6 --out generic.gltf
```

```python
import slice_morph_animation as sm
shape = sm.make_polytope("24cell")
normal = sm.direction_vector(shape, "vertex")
print(sm.section_types(shape, normal))     # [[8, 12, 6], [32, 48, 18], [32, 48, 18], [8, 12, 6]]
animation = sm.build(shape, normal, duration=4.0)
```

`fourd.py` must sit in the same folder.

## Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--polytope` | tesseract | `5cell`, `tesseract`, `16cell` or `24cell`. |
| `--direction` | vertex | Slice normal toward the centroid of the first `cell`, `face`, `edge` or `vertex`, or four numbers `a,b,c,d`. |
| `--duration` | 4 | Seconds for the full sweep; the hyperplane moves at constant speed. |
| `--out` | required | Output `.gltf`. |

## Outputs

`example.gltf` is the tesseract met vertex first: one mesh of 192 vertices and 96 triangles, 6 morph targets, one
animation `slice_sweep` of 4 s on the mesh weights, per-cell vertex colours. Known slice sequences, as
(vertices, edges, faces) per interval between vertex heights:

| Polytope, direction | Sequence |
|---|---|
| tesseract, vertex | tetrahedron (4, 6, 4), truncated tetrahedron (12, 18, 8), the same, tetrahedron; octahedron (6, 12, 8) at the centre |
| tesseract, edge | triangular prism (6, 9, 5), hexagonal prism (12, 18, 8), triangular prism |
| tesseract, face | boxes (8, 12, 6) |
| tesseract, cell | cube (8, 12, 6) |
| 16-cell, cell | cuboctahedron (12, 24, 14) |
| 5-cell, edge | triangular prism (6, 9, 5) |

## Open the glTF

- Blender 2.80 or later: File > Import > glTF 2.0. The morph targets become shape keys and the animation an
  action on them.
- Godot 4: the importer turns morph targets into blend shapes and the animation into an AnimationPlayer track per
  blend shape. At run time, `GLTFDocument.append_from_file` and `generate_scene` give the same nodes.
- three.js: load with `GLTFLoader`, then
  `new THREE.AnimationMixer(gltf.scene).clipAction(gltf.animations[0]).play()` and advance the mixer each frame.

## Limits

Only the four built-in convex polytopes are sliced. The mesh keeps zero-area triangles for the parts of cells the
hyperplane has not reached or has passed. Where heights tie, corners jump inside a 1 ms keyframe pair; the visible
shape does not change. The 3D frame of the slice is the hyperplane basis, fixed for the whole sweep.
