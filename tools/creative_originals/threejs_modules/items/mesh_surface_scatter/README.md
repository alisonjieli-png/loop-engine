# Area-weighted mesh surface scatter

Uniformly distributed points on any triangle mesh. Each sample picks a triangle with probability proportional to its area through a Vose alias table (constant time per draw after a linear setup), then a point inside it with barycentric coordinates `(1 - sqrt(r1), sqrt(r1) (1 - r2), sqrt(r1) r2)`, which is uniform over the triangle. Optional per-vertex weights make the density follow a painted value: triangles are drawn by area times their largest corner weight and each point is kept with the ratio of its interpolated weight to that maximum, so the density is exactly proportional to the interpolated weight. Every sample carries its triangle id, barycentrics and a unit normal, and `surfaceMatrices` stands a model on it.

## When to use it

Use it for grass and moss on terrain meshes, spikes and crystals on creatures, debris on rubble, particle spawn points, decal positions, and any effect that needs points spread evenly over a surface regardless of how the mesh is tessellated.

## Use it

```js
import * as THREE from 'three';
import {scatterOnGeometry, surfaceMatrices} from './mesh_surface_scatter.mjs';

const samples = scatterOnGeometry(rockGeometry, {count: 2000, seed: 4});
const moss = new THREE.InstancedMesh(tuftGeometry, mossMaterial, 2000);
moss.instanceMatrix.array.set(surfaceMatrices(samples, {scaleJitter: 0.3}));
moss.instanceMatrix.needsUpdate = true;
rock.add(moss);   // samples are in the geometry's local space

// Density from a per-vertex value, here the height of each vertex:
const position = rockGeometry.attributes.position;
const weights = Float32Array.from({length: position.count}, (_, i) => Math.max(position.getY(i), 0));
const onTop = scatterOnGeometry(rockGeometry, {count: 500, weights});
```

`demo/scene.mjs` stands 900 spikes on a torus knot, denser toward the top.

## Exports

- `scatterOnSurface(positions, indices = null, options = {})`: `{positions, normals, triangles, barycentrics}` for `count` samples; `Float32Array`s and a `Uint32Array` of triangle ids. Normals are interpolated from `options.normals` when given, else the face normal of the counter-clockwise triangle.
- `scatterOnGeometry(geometry, options = {})`: the same on a `BufferGeometry`'s `position`, index and, unless `options.normals` is given, `normal` attribute. Interleaved attributes are copied out first.
- `surfaceMatrices(samples, options = {})`: one column-major matrix per sample with the model's +Y along the normal, a seeded spin about it, uniform scale and an `offset` along the normal.
- `triangleAreas(positions, indices = null)`: the area of each triangle.
- `buildAliasTable(weights)`: `{probability, alias}` for constant-time weighted sampling.
- `sampleAlias(table, first, second)`: one index from two uniform numbers in [0, 1).
- `SURFACE_SCATTER_DEFAULTS`, `SURFACE_MATRIX_DEFAULTS`: the frozen default options.

## Options

| Option | Function | Default | Meaning |
|---|---|---|---|
| `count` | scatter | 1000 | Number of samples. |
| `seed` | both | 1 / 5 | Integer seed; the same inputs give the same samples. |
| `weights` | scatter | null | Per-vertex relative density. |
| `normals` | scatter | null | Per-vertex normals to interpolate. |
| `scale` | matrices | 1 | Base uniform scale. |
| `scaleJitter` | matrices | 0 | Scale varies by up to this fraction either way, in [0, 1). |
| `spin` | matrices | true | Seeded spin about the normal. |
| `offset` | matrices | 0 | Lift along the normal. |

An unknown option throws `TypeError`; an out-of-range index, count or weight throws `RangeError`.

## Checks

- `test_mesh_surface_scatter.mjs`: triangle areas; the alias table reproduces its weights exactly and never draws a zero weight; two triangles with areas 1:3 share 40,000 samples within five standard deviations of 1:3; every sample lies on its triangle with valid barycentrics; a chi-square over the four midpoint sub-triangles stays under the 0.999 quantile; a weight on one corner moves the mean barycentric of that corner to 1/2 (the analytic value); zero-weight triangles get nothing; interpolated normals are unit length; geometry input equals array input; matrices point +Y along the normal. Known-wrong controls: the barycentric sampler without the square root is refused by the uniformity check, and invalid meshes and options throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks every sample in the browser with three.js `Triangle.closestPointToPoint` on its own triangle, the normals against `Triangle.getNormal`, and the weighted density.

## Limits

Samples are independent, so two points can land very close together; there is no minimum spacing (use Poisson disk scatter for that on flat ground). Per-vertex weights are interpolated linearly within each triangle, so the density pattern follows the mesh resolution. Skinned or morph-animated meshes are sampled in their rest pose. Matrices stand models along the normal with uniform scale and no tangent alignment. The module needs no three.js; the demo was rendered with three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2.

## Technique

- Vose's alias method for weighted triangle choice
- Uniform barycentric sampling with the square root of a uniform number
- Rejection against a per-triangle envelope for per-vertex density
- Shortest-arc quaternion from +Y to the normal
