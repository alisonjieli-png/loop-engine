# Damped look-at tracker with yaw and pitch limits

Aims an object's +Z axis at a target the way a mechanism would. The target direction is expressed in the object's rest frame and split into a yaw (about the rest up axis) and a pitch (about the yawed side axis); both are clamped to limits around the rest orientation; each update moves part of the way there with exponential smoothing and then scales the step so the yaw step plus the pitch step never exceeds `maxSpeed * deltaSeconds`. That sum bounds the true angle turned, so the cap holds for the orientation itself, and limits hold at every moment, not only at the end.

## When to use it

Use it for turrets and cannons, security cameras, character heads and eyes that follow a player, spotlights on a stage, plants turning toward the sun, and any aim that should look mechanical rather than snap.

## Use it

```js
import {LookAtTracker} from './look_at_damped_tracker.mjs';

const tracker = new LookAtTracker({maxSpeed: 2, smoothing: 0.1, yawLimit: 1.2, pitchMin: -0.3, pitchMax: 0.8});
function frame(deltaSeconds) {
  // head is a child of an unrotated base, so world positions work as parent-frame positions
  const {clamped} = tracker.update(head.getWorldPosition(scratch).toArray(), player.position.toArray(), deltaSeconds);
  tracker.applyTo(head);
  warningLight.visible = clamped;
}
```

For an object whose parent is rotated, pass a `restQuaternion` and positions in the parent's frame. `demo/scene.mjs` has three turrets: two aim at an orb, one stops at its yaw limit.

## Exports

- `LookAtTracker`: `new LookAtTracker(options = {}, restQuaternion = [0, 0, 0, 1])`; `update(position, target, deltaSeconds)` returns `{yaw, pitch, quaternion, clamped}`; the `quaternion` getter and `applyTo(object)` give the current orientation; `yaw` and `pitch` hold the state.
- `aimAngles(restQuaternion, position, target)`: the unclamped `{yaw, pitch}` toward the target.
- `clampAim(angles, options = {})`: `{yaw, pitch, clamped}` within the limits.
- `orientationFromAngles(restQuaternion, yaw, pitch)`: rest, then yaw about +Y, then pitch about +X, as `[x, y, z, w]`.
- `stepAngles(current, goal, deltaSeconds, options = {})`: one smoothed, speed-capped update.
- `LOOK_TRACKER_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `maxSpeed` | number | 3 | above 0 | Radians per second, as yaw step plus pitch step. |
| `smoothing` | number | 0.12 | 0 to 60 | Seconds; the time constant of the approach. 0 moves as far as the cap allows. |
| `yawLimit` | number | pi | 0 to pi | Largest yaw either side of rest; pi is unlimited and takes the shorter way round. |
| `pitchMin` | number | -0.6 | -pi/2 to `pitchMax` | Lowest pitch. |
| `pitchMax` | number | 1.0 | `pitchMin` to pi/2 | Highest pitch. |

## Checks

- `test_look_at_damped_tracker.mjs`: aim angles of 45 degrees in yaw and in pitch for hand-picked targets; a rest turned toward +X sees +X straight ahead; the orientation for a yaw of 90 and a pitch of 30 degrees points at (cos 30, sin 30, 0); one capped step from (0, 0) toward (2, 0.5) is exactly (0.24, 0.06), worked by hand; an unlimited yaw crosses pi the short way; in a 600-frame chase of a moving target, no update turns more than `maxSpeed / 60` (the true angle between orientations) and the angles never leave their limits, with and without tight limits; the tracker converges to within 1e-6 of the aim; a target behind pins the yaw at its limit. Known-wrong control: smoothing without the speed cap is refused by the per-update turn check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier simulates three turrets for two seconds in the browser, measures every update's turn with three.js quaternions, and checks that the free turrets aim within 0.001 rad of the orb and the limited one stops at its yaw limit.

## Limits

A kinematic rule, not a motor model: no inertia, torque or overshoot, and the cap bounds the turn per update, not angular acceleration. Yaw and pitch form a gimbal, so a target straight along the rest up axis has no defined yaw and the yaw holds where it was. Position, target and rest must share one frame; `applyTo` writes the local quaternion. The tracked axis is +Z, as three.js `Object3D.lookAt` uses for non-camera objects; a camera needs a rest turned half a turn about Y. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Yaw and pitch of a look direction in a rest frame
- Frame-rate independent exponential smoothing, `1 - exp(-dt / tau)`
- Turn bounded by the sum of the gimbal steps (triangle inequality for rotation angles)
