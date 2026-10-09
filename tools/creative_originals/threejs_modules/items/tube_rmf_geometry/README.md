# Tube along a path with rotation-minimizing frames

A tube swept along a path for three.js, with the cross-section carried by rotation-minimizing frames instead of Frenet frames. Frenet frames follow the curvature, so the cross-section and anything painted on it spin around the path at inflections and flip on straight runs. Rotation-minimizing frames turn only as much as the tangent turns, computed with the double reflection method: reflect the frame in the plane between two samples, then in the plane that maps the reflected tangent onto the next one. A closed loop can still come back twisted (its holonomy); that angle is measured and spread evenly over the loop so the seam closes. The path is a centripetal Catmull-Rom spline through your points (no loops or cusps between close points) or a polyline whose corners are mitred so straight runs keep their radius.

## When to use it

Use it for cables, wires, hoses and pipes, vines and roots, rails and roller coasters, paths with a painted stripe, neon tubes and knots. Use the frames alone to orient anything along a path: fence posts, track sleepers, particles or a camera rig.

## Use it

```js
import * as THREE from 'three';
import {createTubeRmfGeometry, rotationMinimizingFrames, sampleCentripetalCatmullRom} from './tube_rmf_geometry.mjs';

const path = [[0, 0, 0], [1, 0.5, 0.2], [2, 0.1, 0.8], [3, 1, 0.4]];
const cable = createTubeRmfGeometry(THREE, path, {radius: 0.05, radialSegments: 12, samplesPerSegment: 12});
scene.add(new THREE.Mesh(cable, new THREE.MeshStandardMaterial({color: 0x333333, roughness: 0.6})));

// A tapered horn and a mitred pipe:
const horn = createTubeRmfGeometry(THREE, path, {radii: [0.02, 0.06, 0.12, 0.2]});
const pipe = createTubeRmfGeometry(THREE, [[0, 0, 0], [1, 0, 0], [1, 1, 0]], {curve: 'polyline', radius: 0.08});

// Frames for placing objects along the same path:
const samples = sampleCentripetalCatmullRom(path, 12);
const {normals, binormals} = rotationMinimizingFrames(samples.points, samples.tangents);
```

`demo/scene.mjs` renders a trefoil knot with a stripe along it, a tapered horn and a mitred pipe; the verifier compares it with the same knot made by three.js `TubeGeometry`.

## Exports

- `tubeRmfData(points, options = {})`: `{positions, normals, uvs, indices, pathLength}`. Rings of `radialSegments + 1` vertices (the seam repeats for UVs) sit at every sample; triangles are counter-clockwise from outside; u runs along the path by arc length and v around it. A closed tube ends on a copy of its first ring.
- `createTubeRmfGeometry(THREE, points, options = {})`: the same data in a `THREE.BufferGeometry` with an index and computed bounds.
- `sampleCentripetalCatmullRom(points, samplesPerSegment = 8, closed = false)`: `{points, tangents, segments, fractions}`; samples at equal parameter steps that start exactly on each input point, unit tangents from the spline's derivative, and the segment and fraction of each sample. Open ends use reflected phantom points.
- `rotationMinimizingFrames(points, tangents, options = {})`: `{normals, binormals, closingAngle}` with `binormal = tangent x normal`. Options: `closed`, `correctTwist` (default true) and `initialNormal`. `closingAngle` is the loop's twist in radians before correction.
- `TUBE_RMF_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `radius` | number | 0.1 | > 0 | Tube radius when `radii` is null. |
| `radii` | array or null | null | one positive value per point | Radii interpolated linearly along the path. |
| `radialSegments` | integer | 12 | 3 to 1024 | Divisions around the tube. |
| `curve` | string | `'catmull-rom'` | `'catmull-rom'`, `'polyline'` | Spline through the points, or straight segments with mitred corners. |
| `samplesPerSegment` | integer | 8 | 1 to 1024 | Spline samples between consecutive points. |
| `closed` | boolean | false | | The path is a loop; do not repeat the first point. |
| `caps` | boolean | true | | Flat caps on an open tube. |
| `correctTwist` | boolean | true | | Spread a loop's twist so the seam matches. |
| `initialNormal` | `[x, y, z]` or null | null | not along the first tangent | Direction of the first frame. |

An unknown option throws `TypeError`; a value out of range, fewer points than a path needs, or two equal consecutive points throws `RangeError`.

## Checks

- `test_tube_rmf_geometry.mjs`: spline samples at a quarter and a half of a segment, and on an unevenly spaced segment, against values computed independently with the Barry and Goldman pyramid in Python; frames constant on a straight path and closing exactly on a planar circle; on a trefoil (twist about 2.2 radians) every corrected frame is turned by `closingAngle * i / count` and an independent transport (the smallest rotation between tangents) closes on the first frame within 0.03 radians; closed, outward meshes with unit normals; a straight tube, a mitred elbow and a widening tube enclose their polygon prism and frustum volumes; the mitred corner reaches `r sqrt(2)`; a widening tube's normals tilt by the radius slope. Known-wrong controls: the uncorrected trefoil frames miss the first frame by more than 1 radian, and a flipped triangle and a missing triangle fail the solid check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks that the samples equal three.js's own centripetal `CatmullRomCurve3` at the same parameters and that the trefoil's twist was found.

## Limits

The frames are rotation-minimizing between samples (double reflection is a fourth-order approximation), so sparse samples on tight curves drift a little. Spline samples are evenly spaced in the curve parameter, not in arc length, so rings bunch where points are close. Mitres keep straight runs at full radius; a corner sharper than about 170 degrees is capped at a 20 times stretch and pinches. Self-intersection where the path bends tighter than the radius is not detected. Radii vary linearly between points. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Rotation-minimizing frames by double reflection (Wang, Juttler, Zheng and Liu)
- Centripetal Catmull-Rom spline through the Barry and Goldman pyramid, with its analytic derivative
- Even distribution of a closed loop's holonomy angle about each tangent
- Mitre stretch of `1 / cos(half turn)` along the bend direction
