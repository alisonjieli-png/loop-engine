# Trauma camera shake with seeded gradient noise

Camera shake driven by trauma. A hit adds trauma (clamped to 1); trauma falls linearly every second; the shake on each of six channels (right, up and back translation; pitch, yaw and roll) is the channel's amplitude times trauma raised to an exponent times seeded 1D gradient noise. Squaring trauma keeps small hits subtle and big hits violent, and the noise moves smoothly instead of jumping between random offsets. The shake is applied around a base pose you keep, so it never drifts the camera.

## When to use it

Use it for hits, explosions, landings, earthquakes and rumbling engines in games, and for handheld nervousness in cinematics. The same seed and time always give the same shake, so replays and tests are exact.

## Use it

```js
import {CameraShake} from './camera_shake_trauma.mjs';

const shake = new CameraShake({translation: [0.15, 0.15, 0.05], rotation: [0.06, 0.06, 0.1]});
const basePosition = [0, 1.6, 6];
const baseQuaternion = camera.quaternion.toArray();   // the pose your camera rig computed this frame

onHit(() => shake.addTrauma(0.6));
function frame(deltaSeconds) {
  shake.update(deltaSeconds);
  shake.applyTo(camera, basePosition, baseQuaternion);
  renderer.render(scene, camera);
}
```

`shakeOffsets(trauma, time)` gives the raw offsets when you drive something other than a camera (a UI panel, a weapon model, a light). `demo/scene.mjs` shows the view just after a full hit and traces the next 1.4 seconds of the shake.

## Exports

- `CameraShake`: `new CameraShake(options = {})`, then `addTrauma(amount)` (returns the trauma), `update(deltaSeconds)` (advances the clock, decays trauma, returns it), `sample(time = this.time)` and `applyTo(camera, basePosition, baseQuaternion = [0, 0, 0, 1])`. Any object with `position.set(x, y, z)` and `quaternion.set(x, y, z, w)` works, so three.js cameras and objects do.
- `shakeOffsets(trauma, time, options = {})`: `{translation: [x, y, z], rotation: [pitch, yaw, roll], intensity}`.
- `shakeNoise(seed, x)`: seeded 1D gradient noise in [-1, 1], zero on integers, smooth everywhere.
- `traumaAfter(trauma, seconds, decay = 0.8)`: trauma left after linear decay.
- `CAMERA_SHAKE_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `decay` | number | 0.8 | 0 to 100 | Trauma lost per second. |
| `exponent` | number | 2 | 0.5 to 8 | Intensity is trauma to this power. |
| `frequency` | number | 16 | 0 to 200 | Noise cells per second; higher shakes faster. |
| `translation` | 3 numbers | (0.12, 0.12, 0.04) | >= 0 | Largest offsets along the camera's right, up and back axes. |
| `rotation` | 3 numbers | (0.05, 0.05, 0.08) | >= 0 | Largest pitch, yaw and roll in radians. |
| `seed` | integer | 1 | 0 to 2^31 - 1 | Noise seed. |

An unknown option throws `TypeError`; a value out of range throws `RangeError`.

## Checks

- `test_camera_shake_trauma.mjs`: noise values equal an independent Python port of the same integer hash; the noise is zero on the lattice, stays in [-1, 1], changes by less than 0.004 per 0.001 and is deterministic per seed; trauma decays linearly and stops at zero; zero trauma gives zero offsets; offsets stay within their amplitudes; the class saturates trauma, decays it and poses a camera exactly at its base pose once trauma is gone. Known-wrong controls: a noise without the fade curve is refused by the lattice-slope check, and a shake that ignores trauma is refused by the zero-trauma check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks in the browser that zero trauma keeps the base pose exactly, that 281 samples stay within the amplitudes, that trauma reaches zero after 1.4 seconds and that the shaken camera moves within bounds.

## Limits

A procedural game-feel effect, not a model of a physical camera mount: there is no inertia, spring or response to the direction of the hit. The noise is not band-limited, so very high frequencies alias at low frame rates. The shake does not avoid walls or clipping. Trauma decays linearly. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2; frame-time behaviour was not measured.

## Technique

- Trauma-squared shake model with linear trauma decay
- 1D gradient noise: integer lattice hash, gradients in [-1, 1], quintic fade
- Base orientation composed with Euler offsets as quaternions
