# Vertex welding and crease-angle normals

Two clean-up steps for meshes in three.js. `weldVertices` merges vertices that lie within a tolerance of each other, using a hash of tolerance-sized cells and a search of the 27 cells around each point, and returns the unique positions with the triangles rewritten over them. `creaseNormals` then gives every triangle corner the normal of the faces around its vertex that bend by no more than the crease angle, each weighted by the angle the face makes at that vertex, so a cylinder's side turns smooth while its caps stay sharp and a cube keeps its edges. Vertices are split only where two corners end up with different normals, or different UVs when you pass them, so UV seams survive.

## When to use it

Use it on triangle soups from importers, CSG, procedural generators or `toNonIndexed()`, on scanned or exported models whose normals are flat or wrong, on hard-surface props that need sharp edges and smooth curves in one mesh, and before any step that needs shared vertices (outlines, tangents, decimation).

## Use it

```js
import * as THREE from 'three';
import {createCreasedGeometry, creaseNormals, weldVertices} from './crease_normals_welding.mjs';

// Any triangle geometry, indexed or not, rebuilt with sharp edges above 40 degrees:
const rebuilt = createCreasedGeometry(THREE, importedGeometry, 40);
mesh.geometry = rebuilt;

// Typed arrays only (no three.js), for a build step or a worker:
const welded = weldVertices(soupPositions, 1e-5);          // {positions, indices, remap}
const creased = creaseNormals(welded.positions, welded.indices, 30);  // {positions, normals, uvs, indices}
```

`demo/scene.mjs` rebuilds five three.js shapes from triangle soups; the verifier compares them with the flat-shaded soups.

## Exports

- `weldVertices(positions, tolerance = 1e-6, indices = null)`: `{positions, indices, remap}`. `indices` null treats `positions` as a triangle soup; `remap[v]` is the unique vertex of input vertex `v`. A tolerance of 0 merges exact copies only.
- `creaseNormals(positions, indices, creaseAngleDegrees = 30, options = {})`: `{positions, normals, uvs, indices}`; `options.tolerance` sets the weld used to find neighbouring faces and `options.uvs` (two numbers per input vertex) keeps UV seams split. `uvs` is null when none were given.
- `createCreasedGeometry(THREE, geometry, creaseAngleDegrees = 30)`: a new indexed `THREE.BufferGeometry` with `position`, `normal` and (when present) `uv`.
- `CREASE_NORMALS_DEFAULTS`: `{tolerance: 1e-6, creaseAngle: 30}`, frozen.

A position array that is not triples, a soup whose vertex count is not a multiple of three, or bad `indices` throws `TypeError` or `RangeError`; so do a negative tolerance and a crease angle outside 0 to 180 degrees.

## Checks

- `test_crease_normals_welding.mjs`: a cube triangle soup welds to 8 vertices and creases at 30 degrees into 24 with axis normals; a twice-subdivided octahedron sphere welds to `4 * 4^n + 2 = 66` vertices, stays smooth (66 vertices, near-radial normals) at 60 degrees and splits into all 384 corners at 0 degrees; a capped cylinder of 16 segments welds to 34 vertices and creases into `4N + 2 = 66` with only side and cap normals; a 5e-7 offset merges at a tolerance of 1e-6 and not at 1e-9; a UV seam on a flat square keeps 6 vertices instead of 4. Known-wrong control: smoothing across every edge gives the cube diagonal normals, which the cube check refuses.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks, in the browser, that the creased cylinder has only horizontal and vertical normals, that the sphere's normals are radial within a dot product of 0.98, and that the box soup welds to its 8 corners.

## Limits

Welding keeps the first vertex it meets in a cluster, so a chain of points each within the tolerance of the next can merge differently depending on order; it does not repair holes, T-junctions or flipped faces. Each face is compared with every face around a vertex directly rather than by walking the fan, so smoothing is not transitive across a vertex. Degenerate triangles take the plain average around their vertices. `createCreasedGeometry` keeps position and uv only; colours, skin weights and morph targets are dropped. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Spatial hashing in tolerance-sized cells with a 27-cell neighbour search
- Angle-weighted vertex normals (Thurmer and Wuthrich)
- Smoothing by a crease-angle threshold between face normals, with per-corner deduplication by normal and UV
