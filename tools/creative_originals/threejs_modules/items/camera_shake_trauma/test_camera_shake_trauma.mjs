// Known answers for the trauma camera shake: the gradient noise (values from an independent Python port of the same
// integer hash, zero on the lattice, bounded, continuous, deterministic), linear trauma decay, the shake offsets and
// the class that poses a camera. Known-wrong controls: a noise without the fade curve fails the smoothness check,
// and a shake that ignores trauma fails the zero-trauma check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {CAMERA_SHAKE_DEFAULTS, CameraShake, shakeNoise, shakeOffsets, traumaAfter} from './camera_shake_trauma.mjs';

// Problems with a candidate noise function: lattice zeros, range and the slope near the lattice (a smooth fade
// flattens it there: the value one thousandth past a lattice point stays under 0.0021 in magnitude).
function noiseProblems(noise) {
  const problems = [];
  for (let index = -20; index <= 20; index += 1) {
    if (noise(5, index) !== 0) problems.push(`not zero at lattice point ${index}`);
    if (Math.abs(noise(5, index + 0.001)) > 0.0021) problems.push(`too steep just after ${index}`);
  }
  for (let step = 0; step < 4000; step += 1) {
    const value = noise(5, step * 0.0137 - 20);
    if (!(value >= -1 && value <= 1)) problems.push(`out of range: ${value}`);
  }
  return problems.slice(0, 5);
}

test('shakeNoise matches an independent port and has its properties', () => {
  const known = [[1, 0.5, 0.047235894249752164], [3, 2.25, 0.2860312575680837], [1, -0.75, 0.10382627023636815],
    [8, 1.6, 0.41347584349179256]];
  for (const [seed, x, expected] of known) assert.ok(Math.abs(shakeNoise(seed, x) - expected) < 1e-12, `${seed} ${x}`);
  assert.deepEqual(noiseProblems(shakeNoise), []);
  let worst = 0;
  for (let step = 0; step < 20000; step += 1) {
    const x = step * 0.001;
    worst = Math.max(worst, Math.abs(shakeNoise(2, x + 0.001) - shakeNoise(2, x)));
  }
  assert.ok(worst < 0.004, `continuous: the largest change over 0.001 is ${worst}`);
  assert.equal(shakeNoise(9, 3.3), shakeNoise(9, 3.3));
  assert.notEqual(shakeNoise(9, 3.3), shakeNoise(10, 3.3));
});

test('known wrong: a noise that blends linearly instead of with the fade curve is refused', () => {
  const linear = (seed, x) => {
    const index = Math.floor(x);
    const f = x - index;
    const slope = (shakeNoise(seed, index + 0.5) - 0) / 0.5;
    return slope * f * (1 - f) * 2;
  };
  assert.notDeepEqual(noiseProblems(linear), []);
});

test('traumaAfter decays linearly and stops at zero', () => {
  assert.equal(traumaAfter(0.8, 0.5, 0.8), 0.4);
  assert.equal(traumaAfter(0.3, 1, 0.8), 0);
  assert.equal(traumaAfter(1.7, 0, 0.8), 1, 'trauma is clamped to 1');
  assert.throws(() => traumaAfter(0.5, -1, 0.8), RangeError);
});

test('shakeOffsets: zero trauma gives no offset, full trauma the independent values', () => {
  const still = shakeOffsets(0, 1.25);
  assert.deepEqual([...still.translation, ...still.rotation], [0, 0, 0, 0, 0, 0]);
  const full = shakeOffsets(1, 0.3);
  const expected = [0.019520783743972776, -3.405233248668704e-05, 0.005985827347283611, 0.006544230033699603,
    0.017759341219741126, -0.022355729669696442];
  [...full.translation, ...full.rotation].forEach((value, index) => assert.ok(Math.abs(value - expected[index]) < 1e-12));
  const half = shakeOffsets(0.5, 0.3);
  assert.equal(half.intensity, 0.25, 'intensity is trauma squared by default');
  assert.ok(Math.abs(half.translation[0] - 0.004880195935993194) < 1e-12);
  for (let step = 0; step < 500; step += 1) {
    const {translation, rotation} = shakeOffsets(1, step * 0.031);
    translation.forEach((value, axis) => assert.ok(Math.abs(value) <= CAMERA_SHAKE_DEFAULTS.translation[axis]));
    rotation.forEach((value, axis) => assert.ok(Math.abs(value) <= CAMERA_SHAKE_DEFAULTS.rotation[axis]));
  }
});

test('known wrong: a shake that ignores trauma is refused by the zero-trauma check', () => {
  const ignoresTrauma = (trauma, time) => shakeOffsets(1, time);
  const still = ignoresTrauma(0, 1.25);
  assert.notDeepEqual([...still.translation, ...still.rotation], [0, 0, 0, 0, 0, 0]);
});

test('CameraShake adds, decays and poses a camera around its base pose', () => {
  const shake = new CameraShake({decay: 0.5});
  assert.equal(shake.addTrauma(0.6), 0.6);
  assert.equal(shake.addTrauma(0.6), 1, 'trauma saturates at 1');
  assert.equal(shake.update(0.5), 0.75);
  assert.equal(shake.time, 0.5);
  const pose = {
    position: {set(x, y, z) { this.value = [x, y, z]; }},
    quaternion: {set(x, y, z, w) { this.value = [x, y, z, w]; }},
  };
  shake.applyTo(pose, [1, 2, 3]);
  const sample = shake.sample();
  pose.position.value.forEach((value, axis) => assert.ok(Math.abs(value - [1, 2, 3][axis] - sample.translation[axis]) < 1e-12));
  const length = Math.hypot(...pose.quaternion.value);
  assert.ok(Math.abs(length - 1) < 1e-12, 'the shaken orientation is a unit quaternion');
  shake.update(10);
  shake.applyTo(pose, [1, 2, 3], [0, 0.6, 0, 0.8]);
  assert.deepEqual(pose.position.value, [1, 2, 3], 'no trauma left: the base pose exactly');
  assert.deepEqual(pose.quaternion.value, [0, 0.6, 0, 0.8]);
});

test('invalid options and inputs are refused', () => {
  assert.throws(() => new CameraShake({decays: 1}), TypeError);
  assert.throws(() => shakeOffsets(1, 0, {exponent: 0}), RangeError);
  assert.throws(() => shakeOffsets(1, 0, {translation: [1, 2]}), TypeError);
  assert.throws(() => shakeNoise(1.5, 0), TypeError);
  assert.throws(() => new CameraShake().addTrauma(-0.1), RangeError);
  assert.throws(() => new CameraShake({toString: 1}), TypeError, 'an inherited name is not an option');
});
