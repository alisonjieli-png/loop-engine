# Poisson disk scatter with instance matrices

Blue-noise scattering for three.js scenes: points spread evenly but without a grid look, and no two closer than a minimum distance. `poissonDiskPoints` runs Bridson's algorithm with a background grid (cells of `minDistance / sqrt(2)` hold at most one point, so each candidate checks a 5 x 5 block), tries `attempts` candidates in the ring between one and two radii around an active point, and retires the point when none fits. A mask callback shapes the field; when the frontier stops, random restarts find mask regions it could not reach; a density callback then thins the result. `toInstanceMatrices` turns the points into seeded yaw and scale matrices ready for `InstancedMesh`.

## When to use it

Use it for trees, grass clumps, rocks, crowds, props, spawn points, decals and anything that should look naturally spread without overlapping, on a ground plane or a 2D layer.

## Use it

```js
import * as THREE from 'three';
import {poissonDiskPoints, toInstanceMatrices} from './poisson_disk_scatter.mjs';

const points = poissonDiskPoints({
  width: 40, height: 40, originX: -20, originY: -20, minDistance: 1.2, seed: 7,
  mask: (x, z) => Math.hypot(x, z) > 4,               // keep a clearing round the origin
  density: (x, z) => 0.4 + 0.6 * Math.min(Math.max((20 - z) / 40, 0), 1),   // thinner toward +z
});
const trees = new THREE.InstancedMesh(treeGeometry, treeMaterial, points.length / 2);
trees.instanceMatrix.array.set(toInstanceMatrices(points, {scaleJitter: 0.3, seed: 3}));
trees.instanceMatrix.needsUpdate = true;
scene.add(trees);
```

`demo/scene.mjs` grows a forest around a clearing, thinner toward the camera, with rocks scattered inside the clearing.

## Exports

- `poissonDiskPoints(options = {})`: a `Float32Array` `[x0, y0, x1, y1, ...]` of points in `[originX, originX + width) x [originY, originY + height)`, no two closer than `minDistance`. The same options and seed give the same points.
- `toInstanceMatrices(points, options = {})`: a `Float32Array` with one column-major 4 x 4 matrix per point. Plane `'xz'` puts point `(x, y)` at `(x, offset, y)` and spins about +Y; plane `'xy'` puts it at `(x, y, offset)` and spins about +Z.
- `POISSON_DISK_DEFAULTS`, `INSTANCE_MATRIX_DEFAULTS`: the frozen default options.

## Options

| Option | Function | Default | Meaning |
|---|---|---|---|
| `width`, `height` | points | 10, 10 | Field size. |
| `originX`, `originY` | points | 0, 0 | Field corner. |
| `minDistance` | points | 1 | Smallest distance between two points. |
| `attempts` | points | 30 | Candidates per active point (1 to 1000). |
| `seed` | both | 1 / 7 | Integer seed. |
| `maxPoints` | points | 100000 | Stop after this many points. |
| `mask` | points | null | `mask(x, y)` truthy keeps a candidate. |
| `density` | points | null | `density(x, y)` in [0, 1] is the chance each finished point is kept. |
| `plane` | matrices | `'xz'` | `'xz'` or `'xy'`. |
| `offset` | matrices | 0 | Height above the plane. |
| `scale` | matrices | 1 | Base uniform scale. |
| `scaleJitter` | matrices | 0 | Scale varies by up to this fraction either way, in [0, 1). |
| `yawJitter` | matrices | 2 pi | Spin is uniform in [0, `yawJitter`). |

An unknown option throws `TypeError`; an out-of-range value throws `RangeError`.

## Checks

- `test_poisson_disk_scatter.mjs`: brute-force spacing over every pair in three fields; counts between 0.55 and 0.8 points per `minDistance` squared (random sequential packing saturates near 0.6965) and under the hexagonal packing bound; identical points for a seed and different points for another; a disc mask, two separate islands both filled, a shifted origin, density 0 and a binomial check at density 0.5, `maxPoints`; matrices with the right translation, an upright axis, orthogonal axes and a determinant equal to the cube of the scale. Known-wrong controls: uniform random points and a set with one nudged point are refused by the spacing check, and invalid options throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and, in the browser, decomposes every instance matrix with three.js, compares positions and scales with the points, re-measures the closest pair with `Vector2.distanceTo` and checks that the clearing is empty.

## Limits

One minimum distance for the whole field: no variable radius. Density thins finished points, which keeps the spacing but loses the even look where density is low. Restarts find separate mask regions by random tries, so a very small region can be missed. The mask runs for every candidate, so a slow mask slows sampling. The field is a rectangle and points are stored as float32. Matrices spin about one axis with uniform scale; there is no tilt to a slope. The module needs no three.js; the demo was rendered with three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2.

## Technique

- Bridson's fast Poisson disk sampling with a background grid
- Uniform sampling of the ring between one and two radii, by area
- Random restarts for mask regions the frontier cannot reach
