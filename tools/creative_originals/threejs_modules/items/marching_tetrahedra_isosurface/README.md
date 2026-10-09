# Marching tetrahedra isosurface mesher

Turns a scalar field into a triangle mesh for three.js: the surface where the field equals `isoLevel`. Every grid cell is split into six tetrahedra that share the cell's main diagonal; each tetrahedron with corners on both sides of the level contributes one triangle (one corner apart) or two (two and two), placed by linear interpolation along its edges. Because every cell splits its faces along the same diagonals as its neighbours, the surface has no cracks, and because each grid edge produces exactly one vertex the output is welded. Triangles are turned to face from the inside region toward the outside, and normals come from the field's gradient. There is no 256-case lookup table to get wrong.

## When to use it

Use it for metaballs and blobby creatures, signed distance field modelling (unions, blends, cut-outs), caves and overhangs that a heightfield cannot express, medical or scientific volumes, fluid and density visualisation, and any implicit surface you can evaluate as a function.

## Use it

```js
import * as THREE from 'three';
import {createIsosurfaceGeometry, sampleScalarField} from './marching_tetrahedra_isosurface.mjs';

// A smooth union of two spheres as a signed distance field (inside where the value is below 0):
const blend = (a, b, k) => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k / 4; };
const sdf = (x, y, z) => blend(Math.hypot(x - 0.3, y, z) - 0.4, Math.hypot(x + 0.3, y, z) - 0.35, 0.25);
const field = sampleScalarField(sdf, {min: [-1, -1, -1], max: [1, 1, 1], resolution: 64});
const geometry = createIsosurfaceGeometry(THREE, field);
scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0xe0566b})));

// Metaballs are densities: inside where the value is above the level.
const blobs = createIsosurfaceGeometry(THREE, densityField, {isoLevel: 1, insideBelow: false});
```

`demo/scene.mjs` polygonizes five metaballs into one blob; the verifier compares it with five separate spheres.

## Exports

- `sampleScalarField(fn, options = {})`: samples `fn(x, y, z)` on a box. Options `min` and `max` (default -1 and 1 on every axis) and `resolution` (samples per axis, one number or `[nx, ny, nz]`, default 32). Returns `{values, size, min, max}` with `values[x + nx * (y + ny * z)]`; a non-finite sample throws `RangeError`.
- `marchingTetrahedraData(field, options = {})`: `{positions, normals, indices}`. Pass any field of that shape, for example voxels loaded from a file.
- `createIsosurfaceGeometry(THREE, field, options = {})`: the same data in a `THREE.BufferGeometry` with an index and computed bounds.
- `MARCHING_TETRAHEDRA_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `isoLevel` | number | 0 | The level the surface follows. |
| `insideBelow` | boolean | true | Values below the level are inside (signed distances); false for densities. |
| `maxVertices` | integer | 4000000 | Refuse a surface that needs more vertices. |

An unknown option throws `TypeError`; a field of the wrong size, a box with `min` not below `max`, fewer than 2 or more than 1024 samples per axis, or too many vertices throws `RangeError`.

## Checks

- `test_marching_tetrahedra_isosurface.mjs`: a sphere distance field of radius 0.8 at 33 samples per axis gives a closed welded surface (every directed edge once, its reverse once) with Euler characteristic 2, every vertex within 0.01 of the sphere, radial normals and the volume within 2 percent of `4/3 pi r^3`; a torus gives Euler characteristic 0 and two separate balls give 4; a metaball density with `insideBelow: false` gives an outward sphere of radius `sqrt(strength)`; empty and full fields give no triangles; the sampler stores values x-fastest. Known-wrong controls: an unwelded copy of the surface and a flipped triangle fail the closed-surface check.
- `test_contract.mjs`: the exports and the contract examples (one inside corner of a single cell makes 6 triangles on 7 edge midpoints).
- The verifier renders the demo and checks, on the geometry three.js holds, that the blob is closed with Euler characteristic 2, that every vertex has density within 0.08 of the level, and that the gradient normals agree with the face normals three.js averages (mean dot product above 0.99).

## Limits

Linear interpolation along grid edges: features smaller than a cell vanish or merge, sharp edges and corners are rounded off, and vertices sit near but not exactly on the level set. Six tetrahedra per cell make about twice the triangles of marching cubes and some thin slivers; nothing decimates or remeshes them. The surface stays open where it leaves the sampled box, so pad the field. The whole field is held in memory and polygonized on one thread. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Marching tetrahedra on the six-tetrahedron (Kuhn) split of each cube around its main diagonal
- An edge-keyed vertex cache for a welded surface
- Gradient normals from central differences, interpolated along each edge
- Triangle orientation from the inside corners toward the outside corners of each tetrahedron
