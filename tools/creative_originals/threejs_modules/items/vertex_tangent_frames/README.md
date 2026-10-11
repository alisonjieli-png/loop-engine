# Vertex tangent frames for normal mapping

A normal map stores directions in tangent space: x along the texture's u, y along v, z along the surface normal. To use it, a renderer needs a tangent at every vertex. This module finds, for each triangle, the 3D direction in which u increases (and the one in which v increases) from the edge vectors and their UV differences, adds them to the triangle's vertices weighted by the angle the triangle makes there, removes each sum's component along the vertex normal and normalizes it. The fourth component, `w`, records which side the v direction lies on, `+1` or `-1`, so mirrored UVs light correctly. That is exactly the `tangent` attribute three.js materials read: when a geometry has one and the material has a `normalMap`, three.js uses it instead of screen-space derivatives.

## When to use it

Use it for normal-mapped meshes you generate (terrain, lathes, tubes, superellipsoids), imported meshes without tangents, mirrored characters and props, and anywhere the derivative-based fallback shows seams or swimming highlights. It also works in a build step, since `computeVertexTangents` needs no three.js.

## Use it

```js
import * as THREE from 'three';
import {addTangents, computeVertexTangents} from './vertex_tangent_frames.mjs';

const geometry = addTangents(THREE, new THREE.TorusKnotGeometry(0.6, 0.2, 200, 24));
const material = new THREE.MeshStandardMaterial({color: 0xc98a5a, normalMap: tilesNormalMap});
scene.add(new THREE.Mesh(geometry, material));

// Typed arrays only:
const tangents = computeVertexTangents(positions, normals, uvs, indices);  // Float32Array, 4 per vertex
```

`demo/scene.mjs` lights a tiled torus knot and a dimpled sphere through their tangents; the verifier compares it with the same meshes without normal maps.

## Exports

- `computeVertexTangents(positions, normals, uvs, indices = null, options = {})`: a `Float32Array` of `x, y, z, w` per vertex. `indices` null reads the vertices as a triangle soup. With `options.orthogonalize` false the tangent keeps its component along the normal.
- `addTangents(THREE, geometry, options = {})`: computes the tangents from the geometry's `position`, `normal`, `uv` and index and sets them as its `tangent` attribute with item size 4. Returns the geometry; a missing attribute throws `TypeError`.
- `TANGENT_FRAME_DEFAULTS`: `{orthogonalize: true}`, frozen.

A position array that is not triples or an unknown option throws `TypeError`; normals or UVs of the wrong length, or an index out of range, throws `RangeError`.

## Checks

- `test_vertex_tangent_frames.mjs`: a plane with u along x gives `(1, 0, 0, 1)` at every vertex, mirrored u gives `(-1, 0, 0, -1)` and u along y gives `(0, 1, 0, 1)`; a 12-sided cylinder gets the exact circumferential tangent `(-sin phi, 0, cos phi)` with `w = -1` at every vertex, seam included; degenerate UVs give a unit tangent perpendicular to the normal; a triangle soup and the indexed mesh agree. Known-wrong controls: tangents without Gram-Schmidt and a handedness fixed at +1 both fail the cylinder check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks that the tangents of a torus knot agree with three.js's own `BufferGeometry.computeTangents` (mean dot product above 0.99, the same handedness at every vertex) and that both meshes carry a vec4 tangent attribute.

## Limits

This is per-vertex averaging, not the MikkTSpace algorithm: a normal map baked in a tool that uses MikkTSpace can show faint seams or shading differences, most of all on low-poly meshes. Vertices shared across a UV seam or a mirror line average both sides, so split them first (UV seams usually are). Handedness is per vertex, so a triangle whose corners disagree shades with a crease. Degenerate UVs get an arbitrary perpendicular. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Per-triangle tangent and bitangent from UV deltas (Lengyel's method)
- Angle-weighted accumulation of unit directions, then Gram-Schmidt orthogonalization against the normal
- Handedness as the sign of `cross(N, T) . B`
