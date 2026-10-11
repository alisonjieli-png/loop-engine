# Lathe geometry with creases, caps and exact volume

Revolve a 2D profile around the Y axis, the way a lathe turns wood. The profile is a list of `[r, y]` points; each one becomes a ring of vertices at `(r sin phi, y, r cos phi)`. Every profile vertex gets the bisector of its two segment normals, unless the profile turns there by more than `creaseAngle`, in which case it gets two rings so the edge stays sharp (a goblet foot, a bottle shoulder). Open ends off the axis can be closed with flat caps, a closed profile makes a ring or torus, and UVs run around the turn and along the profile by arc length. `latheProfileVolume` gives the exact volume of the solid, which is how much a vase or a bottle holds.

## When to use it

Use it for vases, bottles, cups and goblets, chess pieces, columns and balusters, lamps and lampshades, wheels and rims, rings, and any turned prop. The volume tells you a container's capacity; the area tells you how much paint or material a surface needs.

## Use it

```js
import * as THREE from 'three';
import {createLatheProfileGeometry, latheProfileVolume} from './lathe_profile_geometry.mjs';

// Bottom to top along the outside: the faces point to the right of the profile direction.
const bottle = [[0, 0], [0.3, 0], [0.32, 0.05], [0.32, 0.6], [0.12, 0.8], [0.1, 1.0], [0.12, 1.02]];
const geometry = createLatheProfileGeometry(THREE, bottle, {segments: 64, creaseAngle: 25});
scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0x3f8fbf, roughness: 0.2})));

const litres = latheProfileVolume(bottle) * 1000;  // profile in metres

// A ring from a closed, counter-clockwise loop in the r-y plane:
const loop = Array.from({length: 32}, (_, k) => [0.4 + 0.1 * Math.cos(k * Math.PI / 16), 0.1 * Math.sin(k * Math.PI / 16)]);
const ring = createLatheProfileGeometry(THREE, loop, {closed: true});
```

`demo/scene.mjs` renders a vase, a goblet, a pawn and a ring; the verifier compares it with cylinders in their places.

## Exports

- `latheProfileData(profile, options = {})`: `{positions, normals, uvs, indices}` with triangles counter-clockwise seen from the right-hand side of the profile direction.
- `createLatheProfileGeometry(THREE, profile, options = {})`: the same data in a `THREE.BufferGeometry` with an index and computed bounds.
- `latheProfileVolume(profile, closed = false)`: the signed volume of the full-turn solid, `sum of pi / 3 (r0^2 + r0 r1 + r1^2) (y1 - y0)` over the segments; positive for a profile drawn bottom to top on the outside, or counter-clockwise for a loop.
- `latheProfileArea(profile, closed = false)`: the area of the full-turn surface without caps, `sum of pi (r0 + r1)` times each segment length.
- `LATHE_PROFILE_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `segments` | integer | 48 | 3 to 4096 | Divisions around Y. |
| `phiStart` | number | 0 | any | Angle of the first column, in radians. |
| `phiLength` | number | 2 pi | (0, 2 pi] | Swept angle; less than a full turn leaves the sides open. |
| `creaseAngle` | number | 30 | 0 to 180 | Degrees of turn above which a profile vertex is split into two rings. |
| `caps` | boolean | true | | Close open ends that are off the axis with flat caps (the start faces -Y, the end +Y). |
| `closed` | boolean | false | | The profile is a loop; do not repeat the first point (a repeated one is dropped). |

An unknown option throws `TypeError`; a value out of range, a negative radius, fewer than two points or two equal consecutive points throws `RangeError`.

## Checks

- `test_lathe_profile_geometry.mjs`: the volume and area against the cylinder (2 pi, 4 pi), the cone (`pi r^2 h / 3`, `pi r l`) and the Pappus volume of a polygonal torus section; 198 vertices and 576 indices for a capped cylinder of 48 segments; closed, outward meshes with unit normals and the right Euler characteristic (2 for the cylinder and sphere, 0 for the torus); mesh volumes equal to the profile volume times `(N / 2 pi) sin(2 pi / N)`; the band area equal to `N 2 r sin(pi / N) h`; crease splitting adds rings only past the angle. Known-wrong controls: a volume that treats each segment as a cylinder slice is refused, and a flipped triangle and a missing triangle fail the solid check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks, on the geometry three.js holds, that the vase and the ring enclose the polygon volume of their profiles and that the vase is as tall as its profile.

## Limits

The profile is a polyline: smooth curves need enough points, so sample a spline first. The outside is the right-hand side of the profile direction; a profile drawn top to bottom comes out inside out. Caps are flat discs at the end heights; a partial sweep leaves its two cut faces open. Vertices on the axis repeat once per column, as in `LatheGeometry`. The volume and area describe the smooth surface; the mesh with N segments has the volume times `(N / 2 pi) sin(2 pi / N)`. Self-intersecting profiles are not detected. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Surface of revolution with per-vertex profile normals (the profile normal turned around Y)
- Crease splitting by the turning angle between profile segments
- Frustum volume `pi h / 3 (r0^2 + r0 r1 + r1^2)` summed along the profile, and Pappus's theorems for area and volume
