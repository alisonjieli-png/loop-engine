# Frame-rate independent smooth damp spring

A critically damped spring moves a value toward a target as fast as it can without overshooting. This module steps it with the exact solution of the spring equation, `x(t) = target + (y0 + (v0 + w y0) t) e^(-w t)` with `w = 2 / smoothTime`, instead of integrating it, so one 100 ms step lands where six 16.7 ms steps land and a slow frame never makes the value jump past its target. It works for numbers, for vectors of any length, and for angles along the shorter arc, with an optional speed limit.

## When to use it

Use it for a camera that follows a player, a turret or head that turns toward a target, UI panels and markers that slide into place, zoom levels, audio parameters, or any value that should ease toward a goal the same way at 30, 60 or 144 frames per second.

## Use it

```js
import * as THREE from 'three';
import {SpringFollower, smoothDamp, smoothDampAngle} from './smooth_damp_spring.mjs';

// A camera that follows a target position.
const follow = new SpringFollower(3, {smoothTime: 0.3, maxSpeed: 12});
follow.reset(camera.position.toArray());
function frame(dt) {
  follow.update(player.position.clone().add(offset).toArray(), dt);
  camera.position.fromArray(follow.value);
  camera.lookAt(player.position);
}

// A single number, keeping the velocity between frames.
let zoom = {value: 1, velocity: 0};
zoom = smoothDamp(zoom.value, wantedZoom, zoom.velocity, 0.2, dt);

// A heading in radians that turns the short way round.
let heading = {value: 0, velocity: 0};
heading = smoothDampAngle(heading.value, aim, heading.velocity, 0.15, dt);
```

`demo/scene.mjs` draws a step signal and the spring following it, with and without a speed limit.

## Exports

- `smoothDamp(current, target, velocity, smoothTime, dt, maxSpeed = Infinity)`: one exact step; returns `{value, velocity}`.
- `smoothDampVector(current, target, velocity, smoothTime, dt, maxSpeed = Infinity)`: the same for arrays or typed arrays of equal length; `maxSpeed` limits the length of the motion, so a vector moves in a straight line. Returns new arrays.
- `smoothDampAngle(current, target, velocity, smoothTime, dt, maxSpeed = Infinity)`: the step for an angle in radians along the shorter arc. The value continues from `current` and is not wrapped.
- `shortestAngle(from, to)`: the signed difference along the shorter arc, in (-pi, pi].
- `SpringFollower`: `new SpringFollower(size, options)`, then `reset(value, velocity = null)` and `update(target, dt)`; `value` and `velocity` are `Float64Array`s updated in place.
- `SMOOTH_DAMP_DEFAULTS`: the frozen default options of `SpringFollower`.

## Options

| Option | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `smoothTime` | number | 0.25 | seconds | Time scale; from rest the value covers 59 percent of the distance in one `smoothTime` and 99.7 percent in four. |
| `maxSpeed` | number | Infinity | units per second | Speed a far target is approached at. Infinity for no limit. |

`smoothTime` must be positive, `dt` zero or positive and `maxSpeed` positive; otherwise `RangeError`. Non-finite values throw `TypeError`, an unknown option throws `TypeError`.

With a finite `maxSpeed` the target is pulled toward the value before each step, to the distance at which the stepped motion settles on exactly `maxSpeed * dt` per step: `D = maxSpeed dt (1 - a + a x) / (1 - a)^2` with `x = w dt` and `a = e^(-x)`, which tends to `maxSpeed * smoothTime` for small steps.

## Checks

- `test_smooth_damp_spring.mjs`: one step and 600 short steps against the closed form at four starting states (values computed separately); a zero step changes nothing; from rest the value rises monotonically to the target without passing it; with `maxSpeed` 2 the speed never passes 2 and settles at exactly 2 units per second at 60 Hz, 10 Hz and 4 Hz steps; the vector spring matches the scalar spring per axis and keeps a straight path under its speed limit; angles take the shorter arc through pi; the follower matches `smoothDampVector`. Known-wrong controls: a semi-implicit Euler spring fails the closed-form check, and invalid timing, sizes and options throw.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks in the browser that the spring follows the closed form after the jump, that 40 Hz and 120 Hz runs end at the same value, and that the limited spring respects 1.2 units per second.

## Limits

A critically damped spring only: no under-damped bounce or over-damped settings. The step is exact for a target that holds still during the step, so a target that moves every frame is followed one frame late, as with any per-frame update. With `maxSpeed`, motion from rest stays under the limit only while `dt` is at most `smoothTime / 2`, and a value that already moves faster than the limit slows down over the following steps, not at once. Angles are radians and are not wrapped on output. The module needs no three.js; the demo was rendered with three.js 0.186.1 in headless Chrome on SwiftShader WebGL 2.

## Technique

- Critically damped harmonic oscillator stepped by its exact solution
- Steady-state target distance solved so each step covers `maxSpeed * dt`
- Shortest-arc angle difference
