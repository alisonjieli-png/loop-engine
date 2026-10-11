# Frustum culling for instanced meshes

three.js culls a whole `InstancedMesh` at once, so a forest of 50,000 trees is drawn in full even when the camera sees a tenth of it. This module culls per instance. `frustumPlanes` reads the six planes straight from the view-projection matrix (each plane is the fourth row of the matrix plus or minus another row, the Gribb and Hartmann method) and normalizes them so a plane value is a true distance. `cullInstances` tests each instance's bounding sphere, scaled by the instance's largest axis scale, and copies the visible matrices to the front of the instance buffer, keeping their order; set `InstancedMesh.count` to the number it returns.

## When to use it

Use it for large instanced fields (vegetation, rocks, crowds, buildings, particles drawn as meshes) when the camera sees only part of them, and anywhere you need a cheap sphere or box visibility test against a camera, a light frustum or a portal.

## Use it

```js
import * as THREE from 'three';
import {cullInstances, frustumPlanes} from './frustum_instance_culling.mjs';

const all = trees.instanceMatrix.array.slice();     // keep the full list
const viewProjection = new THREE.Matrix4();
function cull() {
  camera.updateMatrixWorld();
  viewProjection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse).multiply(trees.matrixWorld);
  const planes = frustumPlanes(viewProjection.elements);       // planes in the mesh's own space
  trees.count = cullInstances(all, treeRadius, planes, trees.instanceMatrix.array);
  trees.instanceMatrix.needsUpdate = true;
}
```

Multiply by the mesh's `matrixWorld` as above so the planes live in the instances' space. For a WebGPU renderer pass `{depthZeroToOne: true}` to `frustumPlanes`.

`demo/scene.mjs` culls a 15 x 15 field against a second camera and shows kept blocks in orange.

## Exports

- `frustumPlanes(matrix, options = {})`: a `Float64Array` of 24 numbers, planes `[a, b, c, d]` in the order left, right, bottom, top, near, far, normalized; a point is inside where `a x + b y + c z + d >= 0`.
- `classifySphere(planes, x, y, z, radius)`: `FRUSTUM_RESULT.OUTSIDE`, `INTERSECTS` or `INSIDE`.
- `classifyBox(planes, min, max)`: the same for an axis-aligned box, by its positive and negative corners.
- `cullInstances(source, radius, planes, target, options = {})`: copies every instance not outside to the front of `target` in order and returns the count; `target` may be `source`. `options.center` is the bounding sphere centre in the model's space, `options.indices` (a `Uint32Array`) receives the kept instance numbers.
- `multiplyMatrices(a, b)`: the column-major product `a * b`.
- `FRUSTUM_RESULT`: `{OUTSIDE: 0, INTERSECTS: 1, INSIDE: 2}`.
- `FRUSTUM_CULL_DEFAULTS`: the frozen default options.

## Options

| Option | Function | Default | Meaning |
|---|---|---|---|
| `depthZeroToOne` | `frustumPlanes` | false | Clip z in [0, w] (WebGPU) instead of [-w, w] (WebGL). |
| `center` | `cullInstances` | [0, 0, 0] | Bounding sphere centre in the model's space. |
| `indices` | `cullInstances` | null | A `Uint32Array` that receives the kept instance numbers. |

An unknown option throws `TypeError`; a malformed matrix, a negative radius or a short target throws `RangeError`.

## Checks

- `test_frustum_instance_culling.mjs`: the six planes of a 90 degree, near 1, far 10 projection equal their known values; spheres and boxes inside, intersecting and outside; for 4,000 random points the plane test agrees with the clip-space test `-w <= x, y, z <= w` for a moved camera and for WebGPU depth; compaction keeps order, grows the radius with instance scale, follows an off-centre bounding sphere and works in place. Known-wrong controls: planes read from the transposed matrix disagree on over 100 points, unnormalized planes call a sphere inside that crosses the left plane, and malformed inputs and options throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks in the browser that the kept set equals three.js `Frustum.intersectsSphere` on the same spheres and that the six planes equal three.js's planes.

## Limits

Instances are tested by bounding sphere only, so a long thin model gets a loose sphere and is kept more often than needed. Plane tests are conservative near frustum corners, where a sphere or box just outside two planes counts as intersecting. No occlusion culling and no level of detail. The pass runs on the CPU in time proportional to the instance count; for very large counts a GPU pass or a spatial hierarchy is faster. Compacting in place loses the culled matrices, so keep a full copy to cull again. The module needs no three.js; the demo was rendered with three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2.

## Technique

- Gribb and Hartmann plane extraction from the view-projection matrix
- Signed distance of a bounding sphere to normalized planes
- Positive and negative vertex test for axis-aligned boxes
