# Rounded box geometry with face groups

A box with every edge and corner rounded to one radius, for three.js. Each of the six faces is a grid; every grid point on the sharp box moves to the nearest point of the inner box (the box shrunk by the radius) plus the radius along the unit offset, which lands on the rounded surface, and that offset is the smooth normal. Bevel samples are spaced by equal angles, so highlights run evenly over the edges. The faces keep BoxGeometry's UV layout and material order, so a material array works the same way.

## When to use it

Use it for phones, consoles, furniture, keys and buttons, UI panels in 3D, cushions, dice and any boxy prop that should catch light on its edges.

## Use it

```js
import * as THREE from 'three';
import {createRoundedBoxGeometry, roundedBoxData} from './rounded_box_geometry.mjs';

const geometry = createRoundedBoxGeometry(THREE, {width: 1.2, height: 0.7, depth: 0.9, radius: 0.12, bevelSegments: 6});
scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0xd9744a, roughness: 0.35})));

// Six materials, one per face, in BoxGeometry order (+x, -x, +y, -y, +z, -z):
const dice = new THREE.Mesh(geometry, faceMaterials);

// No three.js needed for the data (in a worker, a build step or Node):
const {positions, normals, uvs, indices, groups} = roundedBoxData({radius: 0.2});
```

`demo/scene.mjs` renders three boxes with different radii; the verifier compares it with the same boxes as sharp `BoxGeometry`.

## Exports

- `roundedBoxData(options = {})`: `{positions, normals, uvs, indices, groups}`. Positions, normals and UVs are `Float32Array`s; indices are a `Uint16Array` (or `Uint32Array` above 65,535 vertices) with triangles counter-clockwise from outside; `groups` is six `{start, count, materialIndex}` rows.
- `createRoundedBoxGeometry(THREE, options = {})`: a `THREE.BufferGeometry` with `position`, `normal` and `uv`, the index, the six groups and computed bounds.
- `roundedBoxVolume(width, height, depth, radius)`: the exact volume of the smooth shape: `8abc + 8r(ab + bc + ca) + 2 pi r^2 (a + b + c) + 4/3 pi r^3` with `a, b, c` the inner half sizes.
- `ROUNDED_BOX_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `width` | number | 1 | > 0 | Size along X. |
| `height` | number | 1 | > 0 | Size along Y. |
| `depth` | number | 1 | > 0 | Size along Z. |
| `radius` | number | 0.1 | 0 to half the smallest size | Rounding radius; 0 gives a sharp box. |
| `bevelSegments` | integer | 4 | 1 to 256 | Divisions of each half bevel (an eighth of a turn). |
| `flatSegments` | integer | 1 | 1 to 256 | Divisions across each flat strip. |

An unknown option throws `TypeError`; a value out of range throws `RangeError`.

## Checks

- `test_rounded_box_geometry.mjs`: 600 vertices and 2,916 indices with the defaults; exact bounds; the mesh is closed (every welded edge shared once in each direction), faces outward and has unit normals; its volume is within 0.4 percent under the closed form 2.58486 for a 2 x 1 x 1.4 box of radius 0.25; radius 0 gives the 2.8 volume box; radius 0.5 on a unit cube puts every vertex on the sphere of radius 0.5. Known-wrong controls: one flipped triangle and one removed triangle are refused by the solid check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks each geometry's bounds and six groups in the browser.

## Limits

One radius for every edge: no per-edge radii, chamfers or custom bevel profiles. Each face is its own grid, so vertices repeat along the twelve face seams (positions and normals match there; UVs do not, as in `BoxGeometry`). Bevel samples are equally spaced in angle along edges and only approximately so at corners, so corner quads are uneven. The mesh volume is slightly under the smooth volume. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Minkowski sum of a box and a ball: nearest inner-box point plus the radius along the unit offset
- Angle-uniform bevel sampling, `t = -(h - r) - r tan(phi)`
- Closed-form rounded box volume (inner box, slabs, quarter cylinders, ball)
