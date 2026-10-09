// Known answers for Poisson disk scattering: every pair at least the minimum distance apart (brute force), a count in
// the band random sequential packing predicts and under the hexagonal packing bound, determinism by seed, masks,
// disconnected mask regions, density thinning and the instance matrices. Uniform random points and a nudged point
// are the known-wrong sets the spacing check must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  INSTANCE_MATRIX_DEFAULTS, POISSON_DISK_DEFAULTS, poissonDiskPoints, toInstanceMatrices,
} from './poisson_disk_scatter.mjs';

// Pairs closer than the minimum distance, by brute force over all pairs (float32 rounding allowed).
function spacingProblems(points, minDistance) {
  const problems = [];
  const count = points.length / 2;
  const limit = minDistance * (1 - 1e-6);
  for (let i = 0; i < count; i += 1) {
    for (let j = i + 1; j < count; j += 1) {
      const distance = Math.hypot(points[2 * i] - points[2 * j], points[2 * i + 1] - points[2 * j + 1]);
      if (distance < limit) problems.push(`points ${i} and ${j} are ${distance} apart`);
    }
  }
  return problems.slice(0, 5);
}

test('every pair is at least minDistance apart and the count fits packing theory', () => {
  for (const [width, height, minDistance, seed] of [[10, 6, 0.5, 3], [20, 20, 1, 9], [8, 8, 0.25, 2]]) {
    const points = poissonDiskPoints({width, height, minDistance, seed});
    assert.deepEqual(spacingProblems(points, minDistance), []);
    const count = points.length / 2;
    // Random sequential packing saturates near 0.6965 / r^2 (coverage 0.547 of disks of radius r / 2); the field edge
    // lets a small field hold a little more. Hexagonal packing, 2 / (sqrt(3) r^2), bounds any spacing-r set.
    const perArea = (count * minDistance * minDistance) / (width * height);
    assert.ok(perArea > 0.55 && perArea < 0.8, `${count} points give ${perArea} per r^2`);
    const expanded = (width + minDistance) * (height + minDistance);
    assert.ok(count <= (expanded * 2) / (Math.sqrt(3) * minDistance * minDistance));
    for (let k = 0; k < count; k += 1) {
      assert.ok(points[2 * k] >= 0 && points[2 * k] < width && points[2 * k + 1] >= 0 && points[2 * k + 1] < height);
    }
  }
});

test('known wrong: uniform random points and a nudged point are refused by the spacing check', () => {
  const points = poissonDiskPoints({width: 6, height: 6, minDistance: 0.5, seed: 4});
  let state = 12345;
  const uniform = points.map(() => {
    state = (Math.imul(state, 1103515245) + 12345) >>> 0;
    return (state / 4294967296) * 6;
  });
  assert.notDeepEqual(spacingProblems(uniform, 0.5), []);
  const nudged = Float32Array.from(points);
  nudged[2] = nudged[0] + 0.2;
  nudged[3] = nudged[1];
  assert.notDeepEqual(spacingProblems(nudged, 0.5), []);
});

test('the same seed gives the same points, another seed others', () => {
  const first = poissonDiskPoints({width: 5, height: 5, minDistance: 0.4, seed: 11});
  const again = poissonDiskPoints({width: 5, height: 5, minDistance: 0.4, seed: 11});
  const other = poissonDiskPoints({width: 5, height: 5, minDistance: 0.4, seed: 12});
  assert.deepEqual(Array.from(again), Array.from(first));
  assert.notDeepEqual(Array.from(other), Array.from(first));
});

test('masks, disconnected regions, origin and density thinning', () => {
  const insideDisc = (x, y) => Math.hypot(x - 5, y - 5) < 3;
  const disc = poissonDiskPoints({width: 10, height: 10, minDistance: 0.5, seed: 5, mask: insideDisc});
  assert.ok(disc.length / 2 > 60);
  for (let k = 0; k < disc.length; k += 2) assert.ok(insideDisc(disc[k], disc[k + 1]));
  const twoIslands = (x, y) => Math.hypot(x - 2, y - 2) < 1.2 || Math.hypot(x - 8, y - 8) < 1.2;
  const islands = poissonDiskPoints({width: 10, height: 10, minDistance: 0.4, seed: 6, mask: twoIslands});
  let near = 0;
  let far = 0;
  for (let k = 0; k < islands.length; k += 2) {
    if (islands[k] < 5) near += 1;
    else far += 1;
  }
  assert.ok(near > 10 && far > 10, `both islands are filled: ${near} and ${far}`);
  const shifted = poissonDiskPoints({width: 4, height: 4, originX: -2, originY: 10, minDistance: 0.5, seed: 1});
  for (let k = 0; k < shifted.length; k += 2) {
    assert.ok(shifted[k] >= -2 && shifted[k] < 2 && shifted[k + 1] >= 10 && shifted[k + 1] < 14);
  }
  const full = poissonDiskPoints({width: 8, height: 8, minDistance: 0.4, seed: 8});
  assert.equal(poissonDiskPoints({width: 8, height: 8, minDistance: 0.4, seed: 8, density: () => 0}).length, 0);
  const half = poissonDiskPoints({width: 8, height: 8, minDistance: 0.4, seed: 8, density: () => 0.5}).length / 2;
  const total = full.length / 2;
  // A binomial(total, 0.5) count stays within five standard deviations of total / 2.
  assert.ok(Math.abs(half - total / 2) < 5 * Math.sqrt(total / 4), `${half} of ${total}`);
  assert.equal(poissonDiskPoints({width: 8, height: 8, minDistance: 0.4, seed: 8, maxPoints: 10}).length, 20);
});

test('toInstanceMatrices places, spins and scales a model at every point', () => {
  const points = Float32Array.from([1, 2, -3, 0.5]);
  const matrices = toInstanceMatrices(points, {offset: 0.25, scale: 2, scaleJitter: 0.2, seed: 3});
  assert.equal(matrices.length, 32);
  for (let index = 0; index < 2; index += 1) {
    const m = matrices.subarray(index * 16, index * 16 + 16);
    assert.deepEqual([m[12], m[13], m[14], m[15]], [points[2 * index], 0.25, points[2 * index + 1], 1]);
    const size = Math.hypot(m[0], m[1], m[2]);
    assert.ok(size >= 1.6 - 1e-6 && size <= 2.4 + 1e-6, `scale ${size}`);
    assert.ok(Math.abs(Math.hypot(m[4], m[5], m[6]) - size) < 1e-5 && Math.abs(m[5] - size) < 1e-5, 'up stays up');
    assert.ok(Math.abs(m[0] * m[8] + m[1] * m[9] + m[2] * m[10]) < 1e-5, 'the axes stay orthogonal');
    const determinant = m[0] * (m[5] * m[10] - m[9] * m[6]) - m[4] * (m[1] * m[10] - m[9] * m[2]) + m[8] * (m[1] * m[6] - m[5] * m[2]);
    assert.ok(Math.abs(determinant - size ** 3) < 1e-4, 'a pure rotation and uniform scale');
  }
  const flat = toInstanceMatrices(Float32Array.from([4, 5]), {plane: 'xy', yawJitter: 0, offset: -1});
  assert.deepEqual(Array.from(flat), [1, 0, 0, 0, -0, 1, 0, 0, 0, 0, 1, 0, 4, 5, -1, 1]);
  assert.equal(INSTANCE_MATRIX_DEFAULTS.plane, 'xz');
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => poissonDiskPoints({minDistance: 0}), RangeError);
  assert.throws(() => poissonDiskPoints({width: -1}), RangeError);
  assert.throws(() => poissonDiskPoints({attempts: 0}), RangeError);
  assert.throws(() => poissonDiskPoints({mask: 'inside'}), TypeError);
  assert.throws(() => poissonDiskPoints({radius: 1}), TypeError);
  assert.throws(() => poissonDiskPoints({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => toInstanceMatrices(Float32Array.from([1, 2]), {valueOf: 1}), TypeError);
  assert.throws(() => toInstanceMatrices(Float32Array.from([1]), {}), RangeError);
  assert.throws(() => toInstanceMatrices(Float32Array.from([1, 2]), {plane: 'yz'}), RangeError);
  assert.throws(() => toInstanceMatrices(Float32Array.from([1, 2]), {scaleJitter: 1}), RangeError);
  assert.equal(POISSON_DISK_DEFAULTS.attempts, 30);
});
