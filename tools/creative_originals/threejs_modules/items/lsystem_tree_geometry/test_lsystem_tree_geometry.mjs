// Known answers for the L-system tree: the algae system's Fibonacci lengths and strings, Koch-style growth counts,
// seeded stochastic rules that repeat by seed, the turtle's segments for every command at 90 degrees, the branch mesh
// counts, lateral area, outward faces and taper-tilted normals, and the three.js geometry. Known-wrong controls: a
// rewrite that replaces symbols rule by rule in place, and a turtle with yaw and pitch swapped, are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LSYSTEM_TREE_DEFAULTS, createLsystemTreeGeometry, interpretTurtle, lsystemTreeData, rewriteLSystem,
} from './lsystem_tree_geometry.mjs';

const ALGAE = {A: 'AB', B: 'A'};

function algaeProblems(rewrite) {
  const lengths = [1, 2, 3, 5, 8, 13, 21, 34];
  const problems = lengths.filter((length, n) => rewrite('A', ALGAE, n).length !== length).map((length) => `length ${length}`);
  if (rewrite('A', ALGAE, 4) !== 'ABAABABA') problems.push('the fourth string');
  return problems;
}

function close(actual, expected, tolerance = 1e-12) {
  return actual.length === expected.length && actual.every((value, k) => Math.abs(value - expected[k]) <= tolerance);
}

// Where the first segment of each command string ends, at 90 degrees and unit length.
const ENDS = [
  ['F', [0, 1, 0]], ['+F', [-1, 0, 0]], ['-F', [1, 0, 0]], ['&F', [0, 0, -1]], ['^F', [0, 0, 1]], ['\\+F', [0, 0, 1]],
  ['/+F', [0, 0, -1]], ['|F', [0, -1, 0]], ['fF', [0, 2, 0]], ['"F', [0, 0.5, 0]],
];

function turtleProblems(interpret) {
  return ENDS.filter(([commands, end]) => !close(interpret(commands, {angle: 90, lengthScale: 0.5}).segments[0].end, end, 1e-12))
    .map(([commands]) => commands);
}

test('rewriteLSystem grows the algae system by Fibonacci numbers', () => {
  assert.deepEqual(algaeProblems(rewriteLSystem), []);
  assert.equal(rewriteLSystem('A', ALGAE, 3), 'ABAAB');
  const koch = rewriteLSystem('F', {F: 'F+F-F-F+F'}, 2);
  assert.equal(koch.length, 49);
  assert.equal([...koch].filter((symbol) => symbol === 'F').length, 25);
});

test('known wrong: replacing symbols rule by rule in place is refused', () => {
  const inPlace = (axiom, rules, iterations) => {
    let current = axiom;
    for (let step = 0; step < iterations; step += 1) {
      for (const [symbol, successor] of Object.entries(rules)) current = current.split(symbol).join(successor);
    }
    return current;
  };
  assert.notDeepEqual(algaeProblems(inPlace), []);
});

test('stochastic rules repeat by seed and follow their weights', () => {
  const rules = {F: [{successor: 'F[+F]', weight: 1}, {successor: 'F[-F]', weight: 1}]};
  assert.equal(rewriteLSystem('F', rules, 5, 3), rewriteLSystem('F', rules, 5, 3));
  assert.notEqual(rewriteLSystem('F', rules, 5, 3), rewriteLSystem('F', rules, 5, 4));
  const fixed = {F: [{successor: 'F[+F]', weight: 1}, {successor: 'F[-F]', weight: 0}]};
  assert.equal(rewriteLSystem('F', fixed, 4, 9), rewriteLSystem('F', {F: 'F[+F]'}, 4));
  const grown = rewriteLSystem('F', rules, 6, 11);
  assert.equal(grown.split('+').length - 1 + grown.split('-').length - 1, 2 ** 6 - 1, 'one turn per branch');
});

test('the turtle draws every command where the rotations say', () => {
  assert.deepEqual(turtleProblems(interpretTurtle), []);
  const branched = interpretTurtle('F[+F]F', {angle: 90});
  assert.equal(branched.segments.length, 3);
  assert.ok(close(branched.segments[1].end, [-1, 1, 0]));
  assert.ok(close(branched.segments[2].start, [0, 1, 0]) && close(branched.segments[2].end, [0, 2, 0]));
  const tapered = interpretTurtle('!F', {radius: 0.1, taper: 0.5});
  assert.equal(tapered.segments[0].startRadius, 0.05);
  const leaf = interpretTurtle('FL').leaves[0];
  assert.deepEqual([leaf.position, leaf.heading], [[0, 1, 0], [0, 1, 0]]);
});

test('known wrong: a turtle with yaw and pitch swapped is refused', () => {
  const swapped = (commands, options) => interpretTurtle(commands.replace('+', '#').replace('&', '+').replace('#', '&'), options);
  assert.notDeepEqual(turtleProblems(swapped), []);
});

test('lsystemTreeData makes one open tapered cylinder per F', () => {
  const single = lsystemTreeData('F', {radialSegments: 8, radius: 0.1});
  assert.equal(single.segmentCount, 1);
  assert.equal(single.positions.length / 3, 18);
  assert.equal(single.indices.length, 48);
  let area = 0;
  for (let t = 0; t < single.indices.length; t += 3) {
    const [a, b, c] = [0, 1, 2].map((k) => Array.from(single.positions.subarray(single.indices[t + k] * 3, single.indices[t + k] * 3 + 3)));
    const u = b.map((value, i) => value - a[i]);
    const w = c.map((value, i) => value - a[i]);
    const face = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
    area += Math.hypot(...face) / 2;
    const outward = [(a[0] + b[0] + c[0]) / 3, 0, (a[2] + b[2] + c[2]) / 3];
    assert.ok(face[0] * outward[0] + face[2] * outward[2] > 0, `triangle ${t / 3} faces outward`);
  }
  assert.ok(Math.abs(area - 0.6122934917841437) < 1e-6, `lateral area ${area}`);
  const taper = lsystemTreeData('FF', {radius: 0.1, segmentTaper: 0.5, radialSegments: 6});
  assert.ok(Math.abs(taper.normals[1] - 0.04993761694389223) < 1e-6, 'the normal tilts up the taper');
  const tree = rewriteLSystem('A', {A: 'F[+AL][-AL]'}, 4);
  const data = lsystemTreeData(tree);
  assert.equal(data.segmentCount, [...tree].filter((symbol) => symbol === 'F').length);
  assert.equal(data.leafPositions.length / 3, [...tree].filter((symbol) => symbol === 'L').length);
});

test('invalid rules, strings and options are refused', () => {
  assert.throws(() => rewriteLSystem('A', {AB: 'A'}, 1), TypeError);
  assert.throws(() => rewriteLSystem('A', ALGAE, 65), RangeError);
  assert.throws(() => rewriteLSystem('A', ALGAE, 30, 1, 1000), RangeError);
  assert.throws(() => rewriteLSystem('A', {A: [{successor: 'B', weight: 0}]}, 1), RangeError);
  assert.throws(() => interpretTurtle('F]'), RangeError);
  assert.throws(() => interpretTurtle('F', {branchAngle: 30}), TypeError);
  assert.throws(() => interpretTurtle('F', {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => lsystemTreeData('FFF', {maxSegments: 2}), RangeError);
  assert.throws(() => lsystemTreeData('F', {radialSegments: 2}), RangeError);
  assert.equal(LSYSTEM_TREE_DEFAULTS.angle, 25);
});

test('createLsystemTreeGeometry fills a BufferGeometry with leaf anchors', () => {
  const FakeThree = {
    BufferAttribute: class { constructor(array, itemSize) { Object.assign(this, {array, itemSize}); } },
    BufferGeometry: class {
      constructor() { this.attributes = {}; this.userData = {}; this.bounds = 0; }
      setAttribute(name, attribute) { this.attributes[name] = attribute; }
      setIndex(index) { this.index = index; }
      computeBoundingBox() { this.bounds += 1; }
      computeBoundingSphere() { this.bounds += 1; }
    },
  };
  const geometry = createLsystemTreeGeometry(FakeThree, 'F[+FL]FL', {radialSegments: 5});
  assert.deepEqual(Object.keys(geometry.attributes), ['position', 'normal', 'uv']);
  assert.equal(geometry.attributes.position.array.length, 3 * 2 * 6 * 3);
  assert.equal(geometry.userData.leafPositions.length, 6);
  assert.equal(geometry.bounds, 2);
});
