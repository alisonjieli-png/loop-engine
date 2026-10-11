# Superellipsoid geometry with analytic normals

Barr's superellipsoid for three.js: one generator covers rounded cubes, cushions, pills, ellipsoids, octahedra and star prisms. A point at latitude `eta` and longitude `omega` sits at `(a C(eta)^e1 C(omega)^e2, b S(eta)^e1, c C(eta)^e1 S(omega)^e2)`, where `C` and `S` are cosine and sine raised to a power that keeps their sign. `exponentY` (Barr's epsilon 1) shapes the profile from pole to pole and `exponentXZ` (epsilon 2) the horizontal cross-section: near 0 square, 1 round, 2 a diamond, above 2 pinched into a star. Normals come from the analytic formula with the dual exponents `2 - e`, so they are exact on the surface, not averaged from faces.

## When to use it

Use it for soft props, pebbles, pills and cushions, stylized buildings and furniture, sci-fi panels, game pickups, and any shape that should morph smoothly between a box, a ball and a diamond by changing two numbers. `superellipsoidImplicit` doubles as a cheap inside test for the same shape.

## Use it

```js
import * as THREE from 'three';
import {createSuperellipsoidGeometry, superellipsoidImplicit, superellipsoidVolume} from './superellipsoid_geometry.mjs';

const geometry = createSuperellipsoidGeometry(THREE, {
  radiusX: 1, radiusY: 0.6, radiusZ: 0.8, exponentY: 0.3, exponentXZ: 0.6, widthSegments: 96, heightSegments: 64,
});
scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0xf2c14e, roughness: 0.4})));

const litres = superellipsoidVolume(0.1, 0.06, 0.08, 0.3, 0.6) * 1000;  // metres in, litres out
const inside = superellipsoidImplicit(0.5, 0.2, 0.1, {radiusX: 1, radiusY: 0.6, radiusZ: 0.8, exponentY: 0.3, exponentXZ: 0.6}) < 1;
```

`demo/scene.mjs` renders six exponent pairs with the same radius; the verifier compares it with plain spheres.

## Exports

- `superellipsoidData(options = {})`: `{positions, normals, uvs, indices}` on a latitude-longitude grid of `(widthSegments + 1) x (heightSegments + 1)` vertices, triangles counter-clockwise from outside; the seam and pole rows repeat for UVs as in `SphereGeometry`.
- `createSuperellipsoidGeometry(THREE, options = {})`: the same data in a `THREE.BufferGeometry` with an index and computed bounds.
- `superellipsoidVolume(radiusX, radiusY, radiusZ, exponentY, exponentXZ)`: the exact volume `2 a b c e1 e2 B(e1/2 + 1, e1) B(e2/2, e2/2)`, with the Beta function computed from Stirling's series for log-gamma. It gives `4/3 pi a b c` for exponents 1 and `4/3 a b c` for exponents 2.
- `superellipsoidImplicit(x, y, z, options = {})`: `(|x/a|^(2/e2) + |z/c|^(2/e2))^(e2/e1) + |y/b|^(2/e1)`, below 1 inside and above 1 outside. Options here are the radii and exponents only.
- `SUPERELLIPSOID_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `radiusX` | number | 1 | > 0 | Half size along X. |
| `radiusY` | number | 1 | > 0 | Half size along Y, the pole axis. |
| `radiusZ` | number | 1 | > 0 | Half size along Z. |
| `exponentY` | number | 0.5 | 0.02 to 4 | North-south roundness (epsilon 1). |
| `exponentXZ` | number | 0.5 | 0.02 to 4 | East-west roundness (epsilon 2). |
| `widthSegments` | integer | 48 | 3 to 1024 | Divisions around Y. |
| `heightSegments` | integer | 32 | 2 to 1024 | Divisions from pole to pole. |

An unknown option throws `TypeError`; a value out of range throws `RangeError`.

## Checks

- `test_superellipsoid_geometry.mjs`: the volume for five radius and exponent sets against values computed independently with Python's `math.lgamma` (8 pi for the 1 x 2 x 3 ellipsoid, 8 for its octahedron); 1,617 vertices and 8,928 indices with the defaults; exact bounds and every vertex on the surface (inside-outside value 1 within 2e-5); closed, outward meshes with unit normals for five exponent pairs; the mesh volume within 1 percent under the exact value. Known-wrong controls: the misread formula with `B(e1/2, e1 + 1)`, which doubles every volume, is refused, and a flipped triangle and a missing triangle fail the solid check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo, checks the bounds of all six shapes, and checks that the analytic normals of a sphere-shaped mesh agree with the face-averaged normals three.js computes (mean dot product above 0.995).

## Limits

A latitude-longitude grid: vertices crowd at the poles, and very small exponents bunch the grid against the box edges, so near-cubes need many segments. Exponents above 2 make concave shapes with cusps where the surface has no normal; there the ellipsoid normal of the point is used, an approximation. UVs follow the angles, not arc length, so textures stretch on boxy shapes. For convex shapes the mesh volume is slightly under `superellipsoidVolume`. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Barr superquadric ellipsoid with signed-power trigonometric parametrization
- Analytic normals from the dual exponents `2 - e`
- Volume through Beta functions, log-gamma from Stirling's series after shifting the argument above 10
