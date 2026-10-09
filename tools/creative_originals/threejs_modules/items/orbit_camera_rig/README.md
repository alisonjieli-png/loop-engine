# Frame-rate independent orbit camera rig

An orbit camera as plain state: a target, a radius and two angles (azimuth about +Y from +Z, polar from +Y, the same convention as three.js `Spherical`). Every input changes a goal; `update(dt)` moves the current state toward the goal with `x = goal + (x - goal) e^(-dt / smoothTime)`, which composes exactly, so a 20 Hz device and a 144 Hz device follow the same path. Limits clamp the radius and keep the camera away from the poles. `pan` moves the target along the view's own right and up axes, scaled by the distance, and `panPixels` converts a pointer drag so the point under the pointer stays under it at the target's depth. The rig touches a three.js camera only in `applyTo`.

## When to use it

Use it for model viewers, product configurators, level editors and strategy or city-builder cameras when you want the same feel at every frame rate, your own input mapping (mouse, touch, gamepad, keyboard, scripted moves) and state you can save, restore or animate.

## Use it

```js
import * as THREE from 'three';
import {OrbitCameraRig} from './orbit_camera_rig.mjs';

const rig = new OrbitCameraRig({target: [0, 1, 0], radius: 8, minRadius: 2, maxRadius: 30, smoothTime: 0.12});
let last = null;
canvas.addEventListener('pointermove', (event) => {
  if (!(event.buttons & 1) || !last) { last = event; return; }
  const dx = event.clientX - last.clientX;
  const dy = event.clientY - last.clientY;
  if (event.shiftKey) rig.panPixels(dx, dy, camera.fov, canvas.clientHeight);
  else rig.rotate(-dx * 0.005, -dy * 0.005);
  last = event;
});
canvas.addEventListener('wheel', (event) => rig.dolly(Math.exp(event.deltaY * 0.001)));

function frame(dt) {
  rig.update(dt);
  rig.applyTo(camera);
}
```

`demo/scene.mjs` rotates, dollies and pans a rig over a sculpture garden and renders the settled view.

## Exports

- `OrbitCameraRig`: `new OrbitCameraRig(options)`; `rotate(deltaAzimuth, deltaPolar)`, `dolly(factor)`, `pan(dx, dy)` (in radius units along the view's right and up) and `panPixels(dx, dy, fovDegrees, viewportHeight)` change the goal; `setFromPosition(position, target)` sets both states from a camera placement; `snap()` jumps to the goal; `update(dt)` returns whether it is still moving; `position()` returns the camera position; `applyTo(camera)` sets `position`, `up` and `lookAt`. `current` and `goal` hold `{target, radius, azimuth, polar}`.
- `orbitPosition(target, radius, azimuth, polar)`: the camera position for an orbit state.
- `orbitAngles(position, target)`: `{radius, azimuth, polar}`, the inverse.
- `ORBIT_RIG_DEFAULTS`: the frozen default options.

## Options

| Option | Default | Meaning |
|---|---|---|
| `target` | [0, 0, 0] | Point the camera orbits and looks at. |
| `radius` | 5 | Distance from the target. |
| `azimuth` | 0 | Radians about +Y, from +Z. |
| `polar` | pi / 3 | Radians from +Y. |
| `minRadius`, `maxRadius` | 0.5, 100 | Dolly limits. |
| `minPolar`, `maxPolar` | 0.05, pi - 0.05 | Keeps the camera off the poles. |
| `smoothTime` | 0.12 | Exponential time constant in seconds; 0 snaps to every goal. |

An unknown option throws `TypeError`; inconsistent limits, a non-positive dolly factor, a negative `dt` or a non-finite input throws `RangeError`.

## Checks

- `test_orbit_camera_rig.mjs`: positions on the axes and from the pole, the inverse angles of (3, 4, 0), clamps at both polar limits and both radius limits, convergence to the goal, one 0.1 s step equal to two 0.05 s steps, one time constant covering `1 - 1/e`, pans along +X and +Y seen from +Z and along -Z seen from +X, a 100 by 50 pixel pan at 90 degrees moving the target by exactly (-2, 1, 0), and `applyTo` on a stand-in camera. Known-wrong controls: a rig that moves a fixed fraction per update fails the half-step check, and invalid options and inputs throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks in the browser that the camera equals three.js `Vector3.setFromSphericalCoords` around the target, that the target projects to the centre of the frame, that a 20 Hz run reaches the same state as the 60 Hz run, and the camera distance.

## Limits

No input handling is included: wire pointer, wheel and touch events yourself. Smoothing is first order, so a move starts at full speed; for a spring that starts from rest use the smooth damp item. Up is always +Y and the polar limits keep the camera off the poles; there is no free roll or trackball rotation. Azimuth is unbounded (it never wraps), so smoothing never turns the long way round. `panPixels` is exact at the target's depth only. Only three.js 0.186.1 was run for the demo, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Spherical coordinates with the polar angle from +Y
- Exact exponential smoothing toward goals
- View-plane basis from the orbit angles for panning
- Pixel to world scale `2 r tan(fov / 2) / height`
