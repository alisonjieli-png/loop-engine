# Heightfield terrain with skirts and surface queries

A terrain mesh for three.js from a plain array of heights. Sample `(i, j)` of a `width x depth` grid (row-major, index `j * width + i`) becomes the vertex `(i * cellSize, height * heightScale, j * cellSize)`, centred on the origin by default. Normals come from central differences of the heights, `normalize(-dy/dx, 1, -dy/dz)`, with one-sided differences on the borders, so a plane gets its exact normal everywhere. A stride uses every n-th sample for level of detail; skirts drop four walls down to a base height so gaps between tiles of different detail stay hidden; a bottom closes the block for dioramas, printed maps or cut-away views. `sampleSurfaceHeight` returns the height on the mesh triangles themselves, so objects placed with it sit exactly on what is drawn.

## When to use it

Use it for game and simulation terrain tiles, heightmap imports, procedural landscapes, tabletop and diorama blocks, data surfaces (elevation, density, any function of two variables), and for snapping characters, trees and props to the ground without a raycast.

## Use it

```js
import * as THREE from 'three';
import {createHeightfieldTerrainGeometry, sampleSurfaceHeight} from './heightfield_terrain_geometry.mjs';

const width = 129;
const depth = 129;
const heights = new Float32Array(width * depth);  // fill from a heightmap or a noise function
const cellSize = 0.5;
const heightScale = 12;
const geometry = createHeightfieldTerrainGeometry(THREE, heights, width, depth, {cellSize, heightScale, skirt: true});
scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0x5a7a3a})));

// Put a tree on the ground at world (x, z), with the grid centred on the origin:
const toSample = (world, count) => world / cellSize + (count - 1) / 2;
tree.position.set(x, heightScale * sampleSurfaceHeight(heights, width, depth, toSample(x, width), toSample(z, depth)), z);
```

`demo/scene.mjs` builds a closed diorama block from a procedural 97 x 97 grid; the verifier compares it with a flat slab.

## Exports

- `heightfieldTerrainData(heights, width, depth, options = {})`: `{positions, normals, uvs, indices, columns, rows}`. The top grid comes first (`columns * rows` vertices, u along +x, v toward -z), then the skirt walls (two vertices per border sample per side, normals pointing out), then the bottom grid. Triangles are counter-clockwise seen from outside.
- `createHeightfieldTerrainGeometry(THREE, heights, width, depth, options = {})`: the same data in a `THREE.BufferGeometry` with an index and computed bounds.
- `sampleHeight(heights, width, depth, x, z)`: bilinear height at sample coordinates `x` in `[0, width - 1]` and `z` in `[0, depth - 1]`, clamped, in the units of the array.
- `sampleSurfaceHeight(heights, width, depth, x, z)`: the height on the mesh's own triangles (each cell split from `(i + 1, j)` to `(i, j + 1)`); equal to `sampleHeight` on planar cells.
- `HEIGHTFIELD_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `cellSize` | number | 1 | Distance between samples in scene units. |
| `heightScale` | number | 1 | World y is height times this. |
| `stride` | integer | 1 | Use every stride-th sample; it must divide `width - 1` and `depth - 1`. |
| `skirt` | boolean | false | Walls down to the base on all four sides. |
| `skirtBase` | number or null | null | World y of the base; null is one cell under the lowest point. It may not be above the lowest point. |
| `closeBottom` | boolean | false | A bottom facing down, so the block is closed (needs `skirt`). |
| `center` | boolean | true | Centre the grid on the origin. |

An unknown option throws `TypeError`; a wrong height count, a non-finite height, a stride that does not divide the grid, a base above the terrain or `closeBottom` without `skirt` throws `RangeError`.

## Checks

- `test_heightfield_terrain_geometry.mjs`: a flat field has normals (0, 1, 0) and the expected positions and UVs; a sloped plane has its exact normal at every vertex, borders included, also with a cell size of 2 and a height scale of 3; skirt and LOD counts; a skirted block with a bottom is closed and outward with the prism volume 28.5 under the plane; `sampleHeight` gives 1.5 and 1.75 on a 2 x 2 ramp and `sampleSurfaceHeight` gives 0.5 where bilinear gives 0.5625 on a saddle cell. Known-wrong controls: a normal that forgets to divide by the cell size is refused, and a flipped triangle and a missing triangle fail the solid check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo, drops six three.js `Raycaster` rays onto the block and requires every hit to be within 0.0001 of `sampleSurfaceHeight`, and requires the central-difference normals to agree with the face normals three.js averages (mean dot product above 0.995).

## Limits

A regular grid with one fixed diagonal per cell: no adaptive triangulation, overhangs, caves or vertical cliffs, and the diagonal can show on steep ridges. At a coarser stride the normals still come from the full-resolution field, so lighting stays steady across levels of detail but does not match the coarse triangles exactly. Skirts hide cracks between tiles of different strides; they do not stitch them. `sampleSurfaceHeight` matches the mesh at stride 1 only. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Central-difference normals with one-sided differences at the borders
- Barycentric interpolation on the mesh's own triangle split
- Skirt walls for level-of-detail terrain tiles, closed into a block by a bottom grid
