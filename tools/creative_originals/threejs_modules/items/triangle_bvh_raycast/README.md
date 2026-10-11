# Triangle BVH for fast raycasts

three.js `Raycaster` tests every triangle of a mesh, which is fine for a cube and slow for a 200,000 triangle scan. This module builds a bounding volume hierarchy once and then answers rays in roughly logarithmic time. Building splits each node where the binned surface area heuristic says a ray will do the least work (12 centroid bins per axis by default, leaves of up to 4 triangles), into flat typed arrays: node boxes, child or triangle offsets, and a triangle order. A closest-hit ray visits the nearer child first and prunes every box beyond the best hit so far; an any-hit ray stops at the first triangle it meets. Triangles are tested with the Moller-Trumbore algorithm, double-sided or culled to front or back faces.

## When to use it

Use it for picking on dense meshes, hitscan weapons, line-of-sight and visibility checks, placing objects on scanned or sculpted terrain, mouse-over on large models and any tool that casts many rays per frame against static geometry.

## Use it

```js
import * as THREE from 'three';
import {bvhFromGeometry, raycastAnyBVH, raycastBVH} from './triangle_bvh_raycast.mjs';

const bvh = bvhFromGeometry(terrain.geometry);   // once, in the geometry's local space

// Rays are in local space: bring a world ray in with the inverse world matrix.
const inverse = terrain.matrixWorld.clone().invert();
const origin = raycaster.ray.origin.clone().applyMatrix4(inverse);
const direction = raycaster.ray.direction.clone().transformDirection(inverse);
const hit = raycastBVH(bvh, origin.toArray(), direction.toArray());
if (hit) marker.position.fromArray(hit.point).applyMatrix4(terrain.matrixWorld);

const blocked = raycastAnyBVH(bvh, eye, toTarget, {far: distanceToTarget});
```

`demo/scene.mjs` casts a fan of 1,024 rays at a torus knot and draws the hierarchy three levels down.

## Exports

- `buildTriangleBVH(positions, indices = null, options = {})`: the hierarchy `{positions, indices, order, nodeBounds, nodeOffsets, nodeCounts, nodeCount, triangleCount}`. Node 0 is the root; an inner node has `nodeCounts` 0 and its children at `nodeOffsets` and `nodeOffsets + 1`; a leaf holds `nodeCounts` triangles `order[nodeOffsets ...]`.
- `bvhFromGeometry(geometry, options = {})`: the same from a `BufferGeometry`'s `position` attribute and index (interleaved positions are copied out).
- `raycastBVH(bvh, origin, direction, options = {})`: the closest hit `{distance, triangle, barycentric, point}` or `null`. The direction need not be unit length; distances are in world units of the geometry's space; `barycentric` weights the triangle's three corners.
- `raycastAnyBVH(bvh, origin, direction, options = {})`: whether anything is hit between `near` and `far`.
- `describeBVH(bvh)`: `{nodes, leaves, maximumDepth, largestLeaf, triangles}`.
- `BVH_DEFAULTS`, `RAYCAST_DEFAULTS`: the frozen default options.

## Options

| Option | Function | Default | Meaning |
|---|---|---|---|
| `maxLeafTriangles` | build | 4 | Leaves at or under this size are not split (1 to 32). |
| `bins` | build | 12 | Centroid bins per axis (2 to 64). |
| `near` | raycast | 0 | Closest accepted distance. |
| `far` | raycast | Infinity | Farthest accepted distance. |
| `side` | raycast | `'double'` | `'double'`, `'front'` (counter-clockwise faces, as three.js `FrontSide`) or `'back'`. |

An unknown option throws `TypeError`; an index outside the vertices, a zero direction or `near > far` throws `RangeError`.

## Checks

- `test_triangle_bvh_raycast.mjs`: closest hits on 500 random rays over a 600-triangle soup and 300 rays over a sphere mesh equal a brute-force reference that uses a different method (plane hit and signed sub-triangle areas); every triangle sits in exactly one leaf and every box contains its triangles and children; any-hit agrees with closest-hit under a far limit; a ray at a 64 by 128 sphere lands within the inscribed tessellation's depth of the analytic distance, with consistent barycentrics; front, back and double-sided culling; geometry input. Known-wrong controls: a hierarchy with one node box moved away misses rays the brute force hits, and malformed meshes, rays and options throw.
- `test_contract.mjs`: the exports and the contract examples, including a hand-written one-triangle hierarchy.
- The verifier renders the demo and compares all 1,024 rays with three.js `Raycaster.intersectObject` on the same double-sided mesh: the same hit or miss, distance and triangle.

## Limits

For static meshes: the hierarchy references the position and index arrays, so rebuild after editing or animating vertices; skinned and morphed meshes are not followed. Rays are in the geometry's local space, so transform them yourself. A hit exactly on a shared edge may report either triangle. Building is single-threaded, O(n log n), with float64 boxes (48 bytes a node). No ray packets, closest-point queries or mesh-to-mesh collision. The module needs no three.js; the demo was rendered with three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2.

## Technique

- Bounding volume hierarchy with binned surface area heuristic splits
- Slab test for a ray and an axis-aligned box
- Moller-Trumbore ray and triangle intersection
- Nearest-child-first stack traversal with pruning by the best hit
