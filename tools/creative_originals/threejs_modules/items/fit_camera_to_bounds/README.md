# Fit a camera to a sphere or box

"Zoom to fit" done exactly. `fitSphereDistance` returns how far from a sphere's centre a perspective camera must stand so the sphere just fits, using the narrower of the vertical and horizontal fields of view (a portrait viewport is limited by its width). `fitBoxPerspective` frames a box from any view direction as tightly as the aim at its centre allows: in the camera's own basis every corner needs a distance of at least `|x| / tan(half width) - z` and `|y| / tan(half height) - z`, and the largest of those puts one corner exactly on the frame edge (or on the edge shrunk by `margin`). Near and far bracket the box. `fitBoxOrthographic` does the same for an orthographic camera, and `applyFit` sets it all on a three.js camera.

## When to use it

Use it for model and product viewers, thumbnail renders, "focus on selection" in editors, cutscene shots that must keep a group of characters in frame, and shadow or minimap cameras that must cover an area.

## Use it

```js
import * as THREE from 'three';
import {applyFit, fitBoxPerspective, fitSphereDistance} from './fit_camera_to_bounds.mjs';

const box = new THREE.Box3().setFromObject(model);
const fit = fitBoxPerspective(box.min.toArray(), box.max.toArray(), camera.fov, camera.aspect,
  {direction: [-1, -0.7, -1.2], margin: 1.1});
applyFit(camera, fit);
controls.target.fromArray(fit.target);   // if you use orbit controls

// Just a distance for a sphere:
const sphere = box.getBoundingSphere(new THREE.Sphere());
const distance = fitSphereDistance(sphere.radius, camera.fov, camera.aspect);
```

`demo/scene.mjs` frames a small still life and compares it with a hand-placed camera.

## Exports

- `fitSphereDistance(radius, fovDegrees, aspect = 1)`: `radius / sin(half)`, with `half` the narrower of the vertical half-angle and `atan(tan(vertical half) * aspect)`.
- `fitBoxPerspective(min, max, fovDegrees, aspect, options = {})`: `{position, target, up, distance, near, far}`. The camera looks at the box centre along `options.direction`.
- `fitBoxOrthographic(min, max, aspect, options = {})`: `{position, target, up, left, right, top, bottom, near, far}`, with the camera one box diagonal back.
- `applyFit(camera, fit)`: sets `position`, `up`, `lookAt(target)`, `near`, `far`, the orthographic extents when present and `zoom = 1`, then `updateProjectionMatrix()`.
- `FIT_CAMERA_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `direction` | vector | [0, 0, -1] | Where the camera looks, from the camera toward the box. |
| `up` | vector | [0, 1, 0] | Up hint; a different one is used when it is parallel to the direction. |
| `margin` | number | 1 | At least 1; the box fills `1 / margin` of the frame. |
| `depthPadding` | number | 1.05 | At least 1; widens near and far around the box. |

An unknown option throws `TypeError`; a field of view outside (0, 180), a non-positive aspect, an inverted box or a zero direction throws `RangeError`.

## Checks

- `test_fit_camera_to_bounds.mjs`: sphere distances of `sqrt(2)` for radius 1 at 90 degrees, `sqrt(5)` for a 0.5 portrait aspect, 2 for a 60 degree landscape view and a fourth value computed separately; four box fits (a cube, a wide box from three-quarters in a portrait frame, a tall box with a 1.25 margin, a flat box seen straight down) projected through a camera built in the test from the fit, with every corner inside the frame and the depth range and the outermost corner at exactly `1 / margin`; orthographic fits at three aspects; `applyFit` on a stand-in camera. Known-wrong controls: a fit made for a square frame leaves corners outside a portrait frame, and invalid inputs and options throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks in the browser, with three.js `Box3.setFromObject` and `Vector3.project`, that the perspective and orthographic fits put the outermost corner at `1 / margin` with every corner inside the depth range.

## Limits

The camera always aims at the box centre, so the fit is tight for that aim, not the smallest frame over every aim. Boxes are axis-aligned in world space; a rotated object gets the loose box of its rotated bounds. The sphere distance assumes the sphere is on the view axis. `applyFit` resets `zoom` to 1 and sets `up`, so a camera with roll or zoom changes. There is no animation; pair it with a spring for a smooth move. Only three.js 0.186.1 was run for the demo, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Sphere tangent to the narrower half field of view
- Per-corner distance bound in the camera basis
- Orthographic extents widened to the viewport aspect
