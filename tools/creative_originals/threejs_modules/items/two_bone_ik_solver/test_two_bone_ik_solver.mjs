// Known answers for two-bone IK: hand-solved bends toward each pole, full extension and full fold, the shortest-arc
// rotation, and properties over 300 seeded random chains (target reached exactly, bone lengths kept, the mid joint on
// the pole side, the returned rotations turning the old bones onto the new ones). Known-wrong control: a solver that
// always bends toward +Y instead of the pole is refused by the pole-side check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {TWO_BONE_IK_DEFAULTS, applyTwoBoneIK, rotationBetween, solveTwoBoneIK} from './two_bone_ik_solver.mjs';

function close(actual, expected, tolerance, label) {
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) <= tolerance,
    `${label}: [${actual}] against [${expected}]`));
}

function rotate(q, v) {
  const [x, y, z, w] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [v[0] + w * t[0] + y * t[2] - z * t[1], v[1] + w * t[1] + z * t[0] - x * t[2], v[2] + w * t[2] + x * t[1] - y * t[0]];
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const size = (a) => Math.hypot(...a);

function random(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

// Problems with a solver over seeded random reachable chains: the end misses, a bone changes length, or the mid
// joint is not on the pole's side of the root-target line.
function solverProblems(solve) {
  const next = random(17);
  const problems = [];
  for (let trial = 0; trial < 300; trial += 1) {
    const point = () => [next() * 4 - 2, next() * 4 - 2, next() * 4 - 2];
    const root = point();
    const mid = point();
    const end = point();
    const upper = size(sub(mid, root));
    const lower = size(sub(end, mid));
    const direction = point();
    const reach = Math.abs(upper - lower) + (upper + lower - Math.abs(upper - lower)) * (0.1 + 0.8 * next());
    const target = [0, 1, 2].map((k) => root[k] + (direction[k] / size(direction)) * reach);
    const pole = point();
    const result = solve(root, mid, end, target, pole);
    if (size(sub(result.end, target)) > 1e-9) problems.push(`trial ${trial}: misses by ${size(sub(result.end, target))}`);
    if (Math.abs(size(sub(result.mid, root)) - upper) > 1e-9 || Math.abs(size(sub(result.end, result.mid)) - lower) > 1e-9) {
      problems.push(`trial ${trial}: a bone changed length`);
    }
    const axis = sub(target, root).map((value) => value / reach);
    const across = (p) => { const r = sub(p, root); const along = dot(r, axis); return [0, 1, 2].map((k) => r[k] - axis[k] * along); };
    if (dot(across(result.mid), across(pole)) < -1e-9) problems.push(`trial ${trial}: bends away from the pole`);
  }
  return problems.slice(0, 5);
}

test('hand-solved chains bend toward their pole', () => {
  const left = solveTwoBoneIK([0, 0, 0], [0, 1, 0], [0, 2, 0], [0, 1, 1], [0, 0, -5]);
  close(left.mid, [0, 1, 0], 1e-12, 'pole behind: the knee stays at (0, 1, 0)');
  close(left.end, [0, 1, 1], 1e-12, 'the end reaches the target');
  assert.equal(left.reached, true);
  assert.ok(left.distance < 1e-12);
  const right = solveTwoBoneIK([0, 0, 0], [0, 1, 0], [0, 2, 0], [0, 1, 1], [0, 0, 5]);
  close(right.mid, [0, 0, 1], 1e-12, 'pole in front: the knee moves to (0, 0, 1)');
});

test('out of reach the chain straightens toward the target; too close it folds', () => {
  const far = solveTwoBoneIK([0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 5, 0], [0, 0, 1]);
  close(far.mid, [0, 1, 0], 1e-12, 'straight mid');
  close(far.end, [0, 2, 0], 1e-12, 'full extension');
  assert.equal(far.reached, false);
  assert.ok(Math.abs(far.distance - 3) < 1e-12);
  const near = solveTwoBoneIK([0, 0, 0], [2, 0, 0], [3, 0, 0], [0.2, 0, 0], [0, 1, 0]);
  close(near.end, [1, 0, 0], 1e-12, 'the shortest reach is |2 - 1|');
  close(near.mid, [2, 0, 0], 1e-12, 'fully folded');
  const short = solveTwoBoneIK([0, 0, 0], [1, 0, 0], [2, 0, 0], [0, 5, 0], [0, 0, 1], {reachMargin: 0.1});
  close(short.end, [0, 1.8, 0], 1e-12, 'reachMargin keeps the chain 10 percent short');
});

test('rotationBetween is the shortest arc, including opposite vectors', () => {
  close(rotationBetween([1, 0, 0], [0, 2, 0]), [0, 0, Math.SQRT1_2, Math.SQRT1_2], 1e-12, 'a quarter turn about Z');
  close(rotationBetween([0, 0, 3], [0, 0, 1]), [0, 0, 0, 1], 0, 'no turn');
  const half = rotationBetween([1, 0, 0], [-1, 0, 0]);
  close(rotate(half, [1, 0, 0]), [-1, 0, 0], 1e-12, 'a half turn maps x to -x');
  assert.throws(() => rotationBetween([0, 0, 0], [1, 0, 0]), RangeError);
});

test('random chains: reached, lengths kept, bent toward the pole, rotations consistent', () => {
  assert.deepEqual(solverProblems((...args) => solveTwoBoneIK(...args)), []);
  const result = solveTwoBoneIK([0.3, -0.2, 0.1], [1.1, 0.4, -0.3], [1.9, 1.2, 0.2], [0.4, 1.3, 0.9], [2, 0, 2]);
  close(rotate(result.rootRotation, sub([1.1, 0.4, -0.3], [0.3, -0.2, 0.1])), sub(result.mid, [0.3, -0.2, 0.1]), 1e-12,
    'rootRotation turns the old upper bone onto the new one');
  close(rotate(result.midRotation, sub([1.9, 1.2, 0.2], [1.1, 0.4, -0.3])), sub(result.end, result.mid), 1e-12,
    'midRotation turns the old lower bone onto the new one');
});

test('known wrong: a solver that bends toward +Y instead of the pole is refused', () => {
  const upward = (root, mid, end, target) => solveTwoBoneIK(root, mid, end, target, [root[0], root[1] + 100, root[2]]);
  assert.notDeepEqual(solverProblems(upward), []);
});

test('invalid inputs are refused', () => {
  assert.throws(() => solveTwoBoneIK([0, 0, 0], [0, 0, 0], [0, 1, 0], [1, 1, 1], [0, 0, 1]), RangeError);
  assert.throws(() => solveTwoBoneIK([0, 0], [0, 1, 0], [0, 2, 0], [1, 1, 1], [0, 0, 1]), TypeError);
  assert.throws(() => solveTwoBoneIK([0, 0, 0], [0, 1, 0], [0, 2, 0], [1, 1, 1], [0, 0, 1], {margin: 0.1}), TypeError);
  assert.throws(() => solveTwoBoneIK([0, 0, 0], [0, 1, 0], [0, 2, 0], [1, 1, 1], [0, 0, 1], {toString: 1}), TypeError,
    'an inherited name is not an option');
  assert.throws(() => solveTwoBoneIK([0, 0, 0], [0, 1, 0], [0, 2, 0], [1, 1, 1], [0, 0, 1], {reachMargin: 0.7}), RangeError);
  assert.throws(() => applyTwoBoneIK({}, null, null, null, [0, 0, 0], [0, 0, 1]), TypeError);
  assert.equal(TWO_BONE_IK_DEFAULTS.reachMargin, 0);
});
