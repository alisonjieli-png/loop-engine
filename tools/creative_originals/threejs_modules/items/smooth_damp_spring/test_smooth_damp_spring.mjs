// Known answers for the critically damped spring: the closed form, independence from the step size, no overshoot from
// rest, the speed limit, the shorter arc for angles and the stateful follower. A semi-implicit Euler spring is the
// known-wrong control the closed-form check must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SMOOTH_DAMP_DEFAULTS, SpringFollower, shortestAngle, smoothDamp, smoothDampAngle, smoothDampVector,
} from './smooth_damp_spring.mjs';

// Values of x(t) = target + (y0 + (v0 + w y0) t) e^(-w t), w = 2 / smoothTime, computed separately with python3.
const CLOSED_FORM = [
  {args: [3, 1, -1, 0.5, 0.3], value: 2.2348962688400285, velocity: -2.8312255919747003},
  {args: [0, 10, 0, 1.0, 1.0], value: 5.939941502901619, velocity: 5.413411329464508},
  {args: [0, 10, 0, 1.0, 0.5], value: 2.6424111765711533, velocity: 7.357588823428847},
  {args: [2.5, -1, 4, 0.25, 0.1], value: 2.0105040595853847, velocity: -9.705505624931986},
];

// Problems with a candidate step function: the closed form after one step, and after 600 short steps.
function closedFormProblems(step) {
  const problems = [];
  for (const {args, value, velocity} of CLOSED_FORM) {
    const [current, target, speed, smoothTime, dt] = args;
    const once = step(current, target, speed, smoothTime, dt);
    if (Math.abs(once.value - value) > 1e-12 || Math.abs(once.velocity - velocity) > 1e-12) {
      problems.push(`one step of ${args} gave ${once.value}, ${once.velocity}`);
    }
    let state = {value: current, velocity: speed};
    for (let k = 0; k < 600; k += 1) state = step(state.value, target, state.velocity, smoothTime, dt / 600);
    if (Math.abs(state.value - value) > 1e-10 || Math.abs(state.velocity - velocity) > 1e-9) {
      problems.push(`600 short steps of ${args} gave ${state.value}, ${state.velocity}`);
    }
  }
  return problems;
}

test('smoothDamp follows the closed form in one step and in many', () => {
  assert.deepEqual(closedFormProblems(smoothDamp), []);
  assert.deepEqual(smoothDamp(4, 1, 2, 0.3, 0), {value: 4, velocity: 2}, 'a zero step changes nothing');
});

test('known wrong: a semi-implicit Euler spring is refused', () => {
  const euler = (current, target, velocity, smoothTime, dt) => {
    const omega = 2 / smoothTime;
    const speed = velocity + (-omega * omega * (current - target) - 2 * omega * velocity) * dt;
    return {value: current + speed * dt, velocity: speed};
  };
  assert.notDeepEqual(closedFormProblems(euler), []);
});

test('from rest the value never overshoots and never stops short', () => {
  let state = {value: 0, velocity: 0};
  let previous = 0;
  for (let k = 0; k < 400; k += 1) {
    state = smoothDamp(state.value, 10, state.velocity, 0.4, 1 / 60);
    assert.ok(state.value >= previous && state.value <= 10, `step ${k}: ${state.value}`);
    previous = state.value;
  }
  assert.ok(10 - state.value < 1e-6, 'after 6.7 s (17 smooth times) the value has arrived');
});

test('maxSpeed caps the speed from rest and cruises at exactly that speed toward a far target', () => {
  for (const dt of [1 / 60, 0.1, 0.25]) {
    let state = {value: 0, velocity: 0};
    let fastest = 0;
    let stride = 0;
    const steps = Math.round(30 / dt);
    for (let k = 0; k < steps; k += 1) {
      const next = smoothDamp(state.value, 100, state.velocity, 0.5, dt, 2);
      stride = (next.value - state.value) / dt;
      fastest = Math.max(fastest, Math.abs(next.velocity), stride);
      state = next;
    }
    assert.ok(fastest <= 2 * (1 + 1e-9), `dt ${dt}: fastest ${fastest}`);
    assert.ok(Math.abs(stride - 2) < 1e-9, `dt ${dt}: the cruise covers 2 per second, got ${stride}`);
    assert.ok(state.value > 58 && state.value < 60, `dt ${dt}: about 2 m/s for 30 s, got ${state.value}`);
  }
});

test('smoothDampVector matches the scalar spring per component and limits the vector speed', () => {
  const vector = smoothDampVector([3, 0, 2.5], [1, 10, -1], [-1, 0, 4], 0.5, 0.3);
  const scalar = [smoothDamp(3, 1, -1, 0.5, 0.3), smoothDamp(0, 10, 0, 0.5, 0.3), smoothDamp(2.5, -1, 4, 0.5, 0.3)];
  scalar.forEach((entry, axis) => {
    assert.ok(Math.abs(vector.value[axis] - entry.value) < 1e-12);
    assert.ok(Math.abs(vector.velocity[axis] - entry.velocity) < 1e-12);
  });
  let value = [0, 0];
  let velocity = [0, 0];
  let fastest = 0;
  for (let k = 0; k < 600; k += 1) {
    ({value, velocity} = smoothDampVector(value, [60, 80], velocity, 0.5, 1 / 60, 3));
    fastest = Math.max(fastest, Math.hypot(velocity[0], velocity[1]));
  }
  assert.ok(fastest <= 3 * (1 + 1e-9) && fastest > 2.9, `vector speed ${fastest}`);
  assert.ok(Math.abs(value[0] / value[1] - 0.75) < 1e-9, 'the path stays on the straight line to the target');
});

test('angles turn along the shorter arc', () => {
  assert.ok(Math.abs(shortestAngle(3, -3) - 0.28318530717958623) < 1e-12);
  assert.ok(Math.abs(shortestAngle(-3, 3) + 0.28318530717958623) < 1e-12);
  assert.equal(shortestAngle(0, Math.PI), Math.PI);
  assert.equal(shortestAngle(0, -Math.PI), Math.PI, 'a half turn is reported as +pi');
  const turned = smoothDampAngle(3, -3, 0, 0.2, 0.05);
  assert.ok(turned.value > 3 && turned.velocity > 0, 'it goes up through pi, not down through zero');
  assert.ok(Math.abs(turned.value - smoothDamp(3, 3.28318530717958623, 0, 0.2, 0.05).value) < 1e-12);
});

test('SpringFollower keeps the state and matches smoothDampVector', () => {
  const follower = new SpringFollower(3, {smoothTime: 0.5});
  follower.reset([3, 0, 2.5], [-1, 0, 4]);
  const value = follower.update([1, 10, -1], 0.3);
  assert.ok(value instanceof Float64Array && value === follower.value);
  const expected = smoothDampVector([3, 0, 2.5], [1, 10, -1], [-1, 0, 4], 0.5, 0.3);
  for (let axis = 0; axis < 3; axis += 1) {
    assert.ok(Math.abs(follower.value[axis] - expected.value[axis]) < 1e-12);
    assert.ok(Math.abs(follower.velocity[axis] - expected.velocity[axis]) < 1e-12);
  }
  assert.equal(SMOOTH_DAMP_DEFAULTS.smoothTime, 0.25);
  assert.equal(new SpringFollower(2).maxSpeed, Infinity);
});

test('known wrong: invalid timing, sizes and options are refused', () => {
  assert.throws(() => smoothDamp(0, 1, 0, 0, 0.1), RangeError);
  assert.throws(() => smoothDamp(0, 1, 0, 0.2, -0.1), RangeError);
  assert.throws(() => smoothDamp(0, 1, 0, 0.2, 0.1, 0), RangeError);
  assert.throws(() => smoothDamp(Number.NaN, 1, 0, 0.2, 0.1), TypeError);
  assert.throws(() => smoothDampVector([0, 0], [1], [0, 0], 0.2, 0.1), RangeError);
  assert.throws(() => new SpringFollower(3, {smoothtime: 1}), TypeError);
  assert.throws(() => new SpringFollower(3, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => new SpringFollower(0), RangeError);
  assert.throws(() => new SpringFollower(2).reset([1, 2, 3]), RangeError);
});
