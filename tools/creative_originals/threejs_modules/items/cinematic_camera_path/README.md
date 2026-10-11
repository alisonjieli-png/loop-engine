# Cinematic camera path at constant speed

A camera path for three.js that passes through keyframe positions on a centripetal Catmull-Rom spline. The centripetal knot spacing (`alpha` 0.5) keeps segments free of cusps and self-loops when keyframes are unevenly spaced. A cumulative arc-length table maps the timeline to distance, so the camera moves at constant speed instead of rushing through long segments; an easing curve on the timeline adds a gentle start and stop. The orientation comes from look targets interpolated on their own spline, from quaternion keyframes slerped per segment, or from the direction of travel.

## When to use it

Use it for fly-throughs, level intros, product turntables, real-estate walk-throughs, replays and any shot that should glide through a set of camera positions you place by hand.

## Use it

```js
import {CameraPath} from './cinematic_camera_path.mjs';

const path = new CameraPath([
  {position: [0, 1.2, 6], target: [0, 1, 0]},
  {position: [4.2, 1.6, 3.8], target: [0, 1.2, 0]},
  {position: [0.6, 3, -5], target: [0, 0.8, 0]},
], {easing: 'smoothstep'});

let elapsed = 0;
function frame(deltaSeconds) {
  elapsed = Math.min(elapsed + deltaSeconds, 8);
  path.applyTo(camera, elapsed / 8);          // an 8-second shot
  renderer.render(scene, camera);
}
```

Keyframes with `quaternion` instead of `target` are slerped; keyframes with neither make the camera look where it is going. `{closed: true}` loops back to the first keyframe. `demo/scene.mjs` draws a path with twelve sampled camera poses.

## Exports

- `CameraPath`: `new CameraPath(keyframes, options = {})`. `sampleAt(t)` gives `{position, quaternion, distance, segment, u}` for `t` in [0, 1]; `applyTo(camera, t)` sets `camera.position` and `camera.quaternion`; `pointAtDistance(distance)` and `locate(distance)` work in arc length; `keyframeFractions()` gives the arc-length fraction of each keyframe; `length`, `segments` and `mode` (`target`, `quaternion` or `tangent`) describe the path.
- `catmullRomPoint(p0, p1, p2, p3, u, alpha = 0.5)`: one point on the segment from `p1` to `p2`.
- `lookRotation(position, target, up = [0, 1, 0])`: the quaternion of a camera at `position` looking at `target` (its -Z axis points at the target).
- `slerpQuaternion(a, b, u)`: spherical linear interpolation along the shorter arc.
- `easeTime(t, easing = 'smoothstep')`: `linear`, `smoothstep` or `smootherstep`, with `t` clamped to [0, 1].
- `CINEMATIC_PATH_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Range | Meaning |
|---|---|---|---|---|
| `alpha` | number | 0.5 | 0 to 1 | Knot spacing exponent: 0 uniform, 0.5 centripetal, 1 chordal. |
| `closed` | boolean | false | | Join the last keyframe to the first. |
| `samplesPerSegment` | integer | 64 | 4 to 4096 | Arc-length table resolution. |
| `easing` | string | `smoothstep` | | Timeline easing. |
| `up` | 3 numbers | (0, 1, 0) | | World up for target and travel orientation. |

Keyframes that mix targets and quaternions, or two consecutive keyframes at the same position, are refused.

## Checks

- `test_cinematic_camera_path.mjs`: Catmull-Rom points against an independent Python port (collinear points stay on the line, an uneven segment gives (1.16142, 0.75106, 0)); the look rotation of a camera on the +X axis is a quarter turn about Y; slerp, easing and a view parallel to up; the path passes through every keyframe within 1e-9, 400 equal time steps differ in length by under 2 percent, every quaternion has unit length and the camera looks at its keyframe targets; a closed ring's table length equals the Python port's 17.8347; slerped quaternion keyframes and travel orientation. Known-wrong control: a sampler that steps the spline parameter instead of the arc length is refused by the constant-speed check.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier renders the demo and checks keyframe pass-through, constant speed, unit quaternions and a posed three.js camera in the browser.

## Limits

Constant speed comes from a piecewise-linear arc-length table: the speed varies by under 2 percent with 64 samples a segment, not exactly zero. Quaternion keyframes are slerped per segment, continuous but not smooth in angular velocity at keyframes (no squad). Target and travel orientations use a fixed world up, so a view straight along up uses a stand-in axis and can roll there. There is no collision, field-of-view or roll keying. Only three.js 0.186.1 was run, in headless Chrome on SwiftShader WebGL 2.

## Technique

- Centripetal Catmull-Rom spline, Barry and Goldman's pyramidal formulation
- Arc-length reparameterization with a cumulative chord table and binary search
- Look rotation from an orthonormal basis to a quaternion; slerp along the shorter arc
