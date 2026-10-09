// Known answers for the orbit rig: positions from the spherical convention, the inverse angles, clamps, convergence,
// two half steps equal to one full step, pans along the view's right and up axes, pixel pans, and placing a camera.
// A rig that moves a fixed fraction per update whatever dt is the known-wrong control the half-step check refuses.
import test from 'node:test';
import assert from 'node:assert/strict';
import {ORBIT_RIG_DEFAULTS, OrbitCameraRig, orbitAngles, orbitPosition} from './orbit_camera_rig.mjs';

function close(actual, expected, tolerance = 1e-12) {
  return actual.length === expected.length && actual.every((value, k) => Math.abs(value - expected[k]) <= tolerance);
}

function snapshot(rig) {
  const {target, radius, azimuth, polar} = rig.current;
  return [...target, radius, azimuth, polar];
}

// Problems with an update rule: one step of 0.1 s must equal two of 0.05 s, from the same goal.
function halfStepProblems(update) {
  const make = () => new OrbitCameraRig({radius: 6, smoothTime: 0.2}).rotate(1.2, 0.4).dolly(0.5).pan(0.3, -0.2);
  const once = make();
  const twice = make();
  update(once, 0.1);
  update(twice, 0.05);
  update(twice, 0.05);
  return close(snapshot(once), snapshot(twice), 1e-12) ? [] : [`${snapshot(once)} differs from ${snapshot(twice)}`];
}

test('positions follow the spherical convention and invert', () => {
  assert.ok(close(orbitPosition([0, 0, 0], 5, 0, Math.PI / 2), [0, 0, 5]));
  assert.ok(close(orbitPosition([0, 0, 0], 5, Math.PI / 2, Math.PI / 2), [5, 0, 0]));
  assert.ok(close(orbitPosition([1, 2, 3], 2, 0, 0), [1, 4, 3]));
  const angles = orbitAngles([3, 4, 0], [0, 0, 0]);
  assert.ok(Math.abs(angles.radius - 5) < 1e-12);
  assert.ok(Math.abs(angles.polar - Math.acos(0.8)) < 1e-12);
  assert.ok(Math.abs(angles.azimuth - Math.PI / 2) < 1e-12);
  assert.ok(close(orbitPosition([0, 0, 0], angles.radius, angles.azimuth, angles.polar), [3, 4, 0]));
});

test('goals clamp to the limits and the current state converges', () => {
  const rig = new OrbitCameraRig({radius: 4, minRadius: 1, maxRadius: 10});
  rig.rotate(0, -10);
  assert.equal(rig.goal.polar, ORBIT_RIG_DEFAULTS.minPolar);
  rig.rotate(0, 20);
  assert.equal(rig.goal.polar, ORBIT_RIG_DEFAULTS.maxPolar);
  rig.dolly(1000);
  assert.equal(rig.goal.radius, 10);
  rig.dolly(1e-6);
  assert.equal(rig.goal.radius, 1);
  rig.rotate(2.5, 0);
  let moving = true;
  for (let frame = 0; frame < 300 && moving; frame += 1) moving = rig.update(1 / 60);
  assert.equal(moving, false);
  assert.ok(close(snapshot(rig), [...rig.goal.target, rig.goal.radius, rig.goal.azimuth, rig.goal.polar], 1e-8));
});

test('smoothing is exact: two half steps equal one full step', () => {
  assert.deepEqual(halfStepProblems((rig, dt) => rig.update(dt)), []);
  const rig = new OrbitCameraRig({smoothTime: 0.2}).rotate(1, 0);
  rig.update(0.2);
  assert.ok(Math.abs(rig.current.azimuth - (1 - Math.exp(-1))) < 1e-12, 'one time constant covers 1 - 1/e');
});

test('known wrong: a fixed fraction per update is refused', () => {
  const fixedFraction = (rig) => {
    for (const key of ['radius', 'azimuth', 'polar']) rig.current[key] += (rig.goal[key] - rig.current[key]) * 0.3;
    for (let axis = 0; axis < 3; axis += 1) rig.current.target[axis] += (rig.goal.target[axis] - rig.current.target[axis]) * 0.3;
  };
  assert.notDeepEqual(halfStepProblems(fixedFraction), []);
});

test('pans move along the view axes, scaled by the radius, and pixel pans follow the pointer', () => {
  const rig = new OrbitCameraRig({radius: 4, polar: Math.PI / 2, azimuth: 0, smoothTime: 0});
  rig.pan(0.5, 0.25);
  assert.ok(close(rig.goal.target, [2, 1, 0]));
  const side = new OrbitCameraRig({radius: 2, polar: Math.PI / 2, azimuth: Math.PI / 2, smoothTime: 0}).pan(1, 0);
  assert.ok(close(side.goal.target, [0, 0, -2]), 'seen from +X the right axis is -Z');
  const pixels = new OrbitCameraRig({radius: 4, polar: Math.PI / 2, azimuth: 0, smoothTime: 0}).panPixels(100, 50, 90, 400);
  // One pixel covers 2 * 4 * tan(45 deg) / 400 = 0.02 units at the target.
  assert.ok(close(pixels.goal.target, [-2, 1, 0], 1e-12));
});

test('setFromPosition, snap and applyTo place a camera', () => {
  const rig = new OrbitCameraRig({smoothTime: 0.5}).setFromPosition([3, 4, 0], [0, 0, 0]);
  assert.ok(close(rig.position(), [3, 4, 0], 1e-12));
  rig.rotate(0.5, 0).snap();
  assert.equal(rig.current.azimuth, rig.goal.azimuth);
  const calls = [];
  const vector = (name) => ({set: (...values) => calls.push([name, ...values])});
  const camera = {position: vector('position'), up: vector('up'), lookAt: (...values) => calls.push(['lookAt', ...values])};
  assert.equal(rig.applyTo(camera), camera);
  assert.ok(close(calls[0].slice(1), rig.position()));
  assert.deepEqual(calls[1], ['up', 0, 1, 0]);
  assert.deepEqual(calls[2], ['lookAt', 0, 0, 0]);
});

test('known wrong: invalid options and inputs are refused', () => {
  assert.throws(() => new OrbitCameraRig({minRadius: 5, maxRadius: 1}), RangeError);
  assert.throws(() => new OrbitCameraRig({maxPolar: 4}), RangeError);
  assert.throws(() => new OrbitCameraRig({speed: 2}), TypeError);
  assert.throws(() => new OrbitCameraRig({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => new OrbitCameraRig().dolly(0), RangeError);
  assert.throws(() => new OrbitCameraRig().update(-1), RangeError);
  assert.throws(() => new OrbitCameraRig().rotate(Number.NaN, 0), RangeError);
  assert.throws(() => orbitAngles([1, 1, 1], [1, 1, 1]), RangeError);
});
