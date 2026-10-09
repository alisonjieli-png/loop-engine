// Known answers for the damped look-at tracker: aim angles toward hand-picked targets, the orientation they give, one
// capped step computed by hand, then a simulated chase: it converges, never turns more than the speed cap allows in
// one update (measured as the true angle between orientations), and never leaves its limits. Known-wrong control: a
// tracker that only smooths, without the speed cap, is refused by the step check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LOOK_TRACKER_DEFAULTS, LookAtTracker, aimAngles, clampAim, orientationFromAngles, stepAngles,
} from './look_at_damped_tracker.mjs';

function rotate(q, v) {
  const [x, y, z, w] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + y * t[2] - z * t[1], v[1] + w * t[1] + z * t[0] - x * t[2], v[2] + w * t[2] + x * t[1] - y * t[0]];
}

function angleBetween(a, b) {
  const dot = Math.abs(a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]);
  return 2 * Math.acos(Math.min(1, dot));
}

// Problems with a stepping rule over a chase of a moving target: a turn larger than maxSpeed * dt in one update,
// or an angle outside its limits.
function chaseProblems(step, options) {
  const settings = {...LOOK_TRACKER_DEFAULTS, ...options};
  const rest = [0, 0, 0, 1];
  let state = {yaw: 0, pitch: 0};
  const problems = [];
  for (let frame = 0; frame < 600; frame += 1) {
    const time = frame / 60;
    const target = [6 * Math.sin(time * 1.7), 4 * Math.sin(time * 0.9) + 1, 6 * Math.cos(time * 2.3)];
    const goal = clampAim(aimAngles(rest, [0, 0, 0], target), options);
    const before = orientationFromAngles(rest, state.yaw, state.pitch);
    state = step(state, goal, 1 / 60, options);
    const turned = angleBetween(before, orientationFromAngles(rest, state.yaw, state.pitch));
    if (turned > settings.maxSpeed / 60 + 1e-9) problems.push(`frame ${frame}: turned ${turned}`);
    if (Math.abs(state.yaw) > settings.yawLimit + 1e-12 || state.pitch < settings.pitchMin - 1e-12
      || state.pitch > settings.pitchMax + 1e-12) problems.push(`frame ${frame}: outside the limits`);
  }
  return problems.slice(0, 5);
}

test('aimAngles and orientationFromAngles agree on hand-picked directions', () => {
  const quarter = aimAngles([0, 0, 0, 1], [0, 0, 0], [1, 0, 1]);
  assert.ok(Math.abs(quarter.yaw - Math.PI / 4) < 1e-12 && Math.abs(quarter.pitch) < 1e-12);
  const up = aimAngles([0, 0, 0, 1], [1, 1, 1], [1, 2, 2]);
  assert.ok(Math.abs(up.yaw) < 1e-12 && Math.abs(up.pitch - Math.PI / 4) < 1e-12);
  const turnedRest = [0, Math.SQRT1_2, 0, Math.SQRT1_2];
  const ahead = aimAngles(turnedRest, [0, 0, 0], [3, 0, 0]);
  assert.ok(Math.abs(ahead.yaw) < 1e-12 && Math.abs(ahead.pitch) < 1e-12, 'a rest turned to +X sees +X straight ahead');
  const forward = rotate(orientationFromAngles([0, 0, 0, 1], Math.PI / 2, Math.PI / 6), [0, 0, 1]);
  [Math.cos(Math.PI / 6), Math.sin(Math.PI / 6), 0].forEach((value, axis) => assert.ok(Math.abs(forward[axis] - value) < 1e-12));
  assert.throws(() => aimAngles([0, 0, 0, 1], [1, 1, 1], [1, 1, 1]), RangeError);
});

test('one capped step, worked by hand', () => {
  const next = stepAngles({yaw: 0, pitch: 0}, {yaw: 2, pitch: 0.5}, 0.1, {maxSpeed: 3, smoothing: 0.12});
  assert.ok(Math.abs(next.yaw - 0.24) < 1e-12 && Math.abs(next.pitch - 0.06) < 1e-12, JSON.stringify(next));
  const free = stepAngles({yaw: 0, pitch: 0}, {yaw: 0.01, pitch: 0}, 0.1, {maxSpeed: 3, smoothing: 0});
  assert.equal(free.yaw, 0.01, 'without smoothing a small gap closes at once');
  const around = stepAngles({yaw: 3, pitch: 0}, {yaw: -3, pitch: 0}, 1, {maxSpeed: 100, smoothing: 0});
  assert.ok(Math.abs(around.yaw + 3) < 1e-12, 'unlimited yaw takes the short way through pi');
});

test('a chase converges, keeps the speed cap and stays inside the limits', () => {
  assert.deepEqual(chaseProblems(stepAngles, {}), []);
  assert.deepEqual(chaseProblems(stepAngles, {yawLimit: 0.8, pitchMin: -0.2, pitchMax: 0.4, maxSpeed: 1.5}), []);
  const tracker = new LookAtTracker({smoothing: 0.05});
  for (let frame = 0; frame < 300; frame += 1) tracker.update([0, 0, 0], [2, 1, 2], 1 / 60);
  const goal = aimAngles([0, 0, 0, 1], [0, 0, 0], [2, 1, 2]);
  assert.ok(Math.abs(tracker.yaw - goal.yaw) < 1e-6 && Math.abs(tracker.pitch - goal.pitch) < 1e-6, 'converged');
  const behind = new LookAtTracker({yawLimit: 1.2});
  let result;
  for (let frame = 0; frame < 300; frame += 1) result = behind.update([0, 0, 0], [0.1, 0, -5], 1 / 60);
  assert.equal(result.clamped, true);
  assert.ok(Math.abs(Math.abs(behind.yaw) - 1.2) < 1e-6, 'a target behind pins the yaw at its limit');
  const pose = {quaternion: {set(...value) { this.value = value; }}};
  behind.applyTo(pose);
  assert.deepEqual(pose.quaternion.value, behind.quaternion);
});

test('known wrong: smoothing without the speed cap is refused', () => {
  const uncapped = (current, goal, deltaSeconds, options) => stepAngles(current, goal, deltaSeconds, {...options, maxSpeed: 1e9});
  assert.notDeepEqual(chaseProblems(uncapped, {}), []);
});

test('invalid options are refused', () => {
  assert.throws(() => new LookAtTracker({speed: 2}), TypeError);
  assert.throws(() => new LookAtTracker({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => stepAngles({yaw: 0, pitch: 0}, {yaw: 1, pitch: 0}, 0.1, {maxSpeed: 0}), RangeError);
  assert.throws(() => clampAim({yaw: 0, pitch: 0}, {pitchMin: 1, pitchMax: 0}), RangeError);
  assert.throws(() => new LookAtTracker({}, [0, 0, 0, 0]), RangeError);
});
