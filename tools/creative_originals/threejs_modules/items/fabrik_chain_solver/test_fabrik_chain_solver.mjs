// Known answers for the FABRIK solver: a target at exactly full reach and one beyond it give hand-computed straight
// chains; over 300 seeded random chains a reachable target is reached within tolerance, every segment keeps its
// length and the root never moves; a pose already at the target takes no pass. Known-wrong control: a solver that
// skips the backward pass (so the root drifts) is refused by the chain check.
import test from 'node:test';
import assert from 'node:assert/strict';
import {FABRIK_DEFAULTS, applyFabrikChain, chainLengths, chainReach, solveFabrik} from './fabrik_chain_solver.mjs';

function close(actual, expected, tolerance, label) {
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) <= tolerance,
    `${label}: [${actual}] against [${expected}]`));
}

function random(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

const dist = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);

// Problems with a solver over random chains of 3 to 9 joints and targets inside their reach, kept a tenth of the
// reachable range away from both ends (where FABRIK converges slowly).
function chainProblems(solve) {
  const next = random(91);
  const problems = [];
  for (let trial = 0; trial < 300; trial += 1) {
    const count = 3 + Math.floor(next() * 7);
    const joints = [[next() - 0.5, next() - 0.5, next() - 0.5]];
    for (let index = 1; index < count; index += 1) {
      const previous = joints[index - 1];
      joints.push([previous[0] + next() - 0.5, previous[1] + 0.3 + next(), previous[2] + next() - 0.5]);
    }
    const lengths = chainLengths(joints);
    const {shortest, longest} = chainReach(joints);
    const direction = [next() - 0.5, next() - 0.5, next() - 0.5];
    const reach = (shortest + (longest - shortest) * (0.1 + 0.8 * next())) / Math.hypot(...direction);
    const target = joints[0].map((value, axis) => value + direction[axis] * reach);
    const result = solve(joints, target);
    if (dist(result.joints[0], joints[0]) !== 0) problems.push(`trial ${trial}: the root moved`);
    if (!(dist(result.joints[result.joints.length - 1], target) <= 1e-4)) problems.push(`trial ${trial}: missed the target`);
    lengths.forEach((value, index) => {
      if (Math.abs(dist(result.joints[index], result.joints[index + 1]) - value) > 1e-9) problems.push(`trial ${trial}: segment ${index}`);
    });
  }
  return problems.slice(0, 5);
}

test('targets at and beyond full reach give straight chains', () => {
  const exact = solveFabrik([[0, 0, 0], [1, 0, 0], [2, 0, 0]], [0, 2, 0]);
  close(exact.joints[1], [0, 1, 0], 1e-12, 'middle joint');
  close(exact.joints[2], [0, 2, 0], 1e-12, 'end joint');
  assert.equal(exact.reachable, false, 'a target at exactly full reach is solved by straightening');
  const far = solveFabrik([[1, 1, 1], [1, 2, 1], [1, 3, 1], [1, 4, 1]], [1, 1, 11]);
  far.joints.forEach((joint, index) => close(joint, [1, 1, 1 + index], 1e-12, `joint ${index}`));
  assert.ok(Math.abs(far.error - 7) < 1e-12);
  assert.equal(far.reached, false);
});

test('random reachable targets: reached, lengths kept, root fixed', () => {
  assert.deepEqual(chainProblems((joints, target) => solveFabrik(joints, target, {maxIterations: 200})), []);
  const already = solveFabrik([[0, 0, 0], [0, 1, 0], [0, 2, 0]], [0.00001, 1.99999, 0]);
  assert.equal(already.iterations, 0);
  assert.equal(already.reached, true);
  const tight = solveFabrik([[0, 0, 0], [0, 1, 0], [1, 1, 0]], [0.5, 0.5, 0.5], {tolerance: 1e-10, maxIterations: 500});
  assert.ok(tight.error <= 1e-10 && tight.reached && tight.iterations > 1);
});

test('known wrong: a solver without the backward pass is refused', () => {
  const forwardOnly = (joints, target) => {
    const lengths = chainLengths(joints);
    const points = joints.map((joint) => [...joint]);
    for (let pass = 0; pass < 32; pass += 1) {
      points[points.length - 1] = [...target];
      for (let index = points.length - 2; index >= 0; index -= 1) {
        const span = dist(points[index + 1], points[index]);
        points[index] = points[index + 1].map((value, axis) => value + (points[index][axis] - value) * (lengths[index] / span));
      }
    }
    return {joints: points};
  };
  assert.notDeepEqual(chainProblems(forwardOnly), []);
});

test('a target closer than the chain can fold is unreachable', () => {
  const joints = [[0, 0, 0], [0, 3, 0], [0, 4, 0]];
  assert.deepEqual(chainReach(joints), {shortest: 2, longest: 4});
  const near = solveFabrik(joints, [0.5, 0, 0], {maxIterations: 500});
  assert.equal(near.reachable, false);
  assert.equal(near.reached, false);
  assert.ok(Math.abs(near.error - 1.5) < 1e-3, `folded as far as it goes: ${near.error}`);
});

test('chainLengths, the iteration cap and invalid inputs', () => {
  assert.deepEqual(chainLengths([[0, 0, 0], [3, 4, 0], [3, 4, 2]]), [5, 2]);
  const capped = solveFabrik([[0, 0, 0], [0, 1, 0], [1, 1, 0]], [0.5, 0.5, 0.5], {tolerance: 1e-12, maxIterations: 1});
  assert.equal(capped.iterations, 1);
  assert.throws(() => chainLengths([[0, 0, 0]]), TypeError);
  assert.throws(() => chainLengths([[0, 0, 0], [0, 0, 0]]), RangeError);
  assert.throws(() => solveFabrik([[0, 0, 0], [0, 1, 0]], [1, 1, 1], {tolerence: 1}), TypeError);
  assert.throws(() => solveFabrik([[0, 0, 0], [0, 1, 0]], [1, 1, 1], {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => solveFabrik([[0, 0, 0], [0, 1, 0]], [1, 1, 1], {maxIterations: 0}), RangeError);
  assert.throws(() => applyFabrikChain({}, [null], [0, 0, 0]), TypeError);
  assert.equal(FABRIK_DEFAULTS.maxIterations, 32);
});
