// Known answers for mesh surface scattering: triangle areas, the alias table's exact probabilities, an area ratio of
// 3 to 1 met within five standard deviations, every point on its triangle, uniformity inside a triangle (a chi-square
// over the four midpoint sub-triangles), per-vertex density with its known barycentric mean, normals and matrices.
// The known-wrong control is the barycentric sampler without the square root, which the uniformity check refuses.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SURFACE_MATRIX_DEFAULTS, SURFACE_SCATTER_DEFAULTS, buildAliasTable, sampleAlias, scatterOnGeometry, scatterOnSurface,
  surfaceMatrices, triangleAreas,
} from './mesh_surface_scatter.mjs';

// Two triangles in the z = 0 plane: areas 0.5 and 1.5.
const TWO = Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 0, 0, 5, 0, 0, 2, 1, 0]);

// Chi-square of samples over the four midpoint sub-triangles of one triangle (each should hold a quarter): a sample
// with barycentrics (a, b, c) lies in the corner triangle of the corner whose coordinate exceeds 1/2, else in the
// middle one.
function quarterChiSquare(barycentrics) {
  const counts = [0, 0, 0, 0];
  const total = barycentrics.length / 3;
  for (let k = 0; k < total; k += 1) {
    const a = barycentrics[3 * k];
    const b = barycentrics[3 * k + 1];
    const c = barycentrics[3 * k + 2];
    counts[a > 0.5 ? 0 : b > 0.5 ? 1 : c > 0.5 ? 2 : 3] += 1;
  }
  return counts.reduce((sum, count) => sum + (count - total / 4) ** 2 / (total / 4), 0);
}

test('triangleAreas and the alias table reproduce their weights exactly', () => {
  assert.deepEqual(Array.from(triangleAreas(TWO)), [0.5, 1.5]);
  const weights = [0.5, 1.5, 0, 3, 1];
  const table = buildAliasTable(weights);
  const total = weights.reduce((sum, value) => sum + value, 0);
  const reached = new Array(weights.length).fill(0);
  for (let i = 0; i < weights.length; i += 1) {
    reached[i] += table.probability[i];
    reached[table.alias[i]] += 1 - table.probability[i];
  }
  reached.forEach((value, i) => assert.ok(Math.abs(value / weights.length - weights[i] / total) < 1e-12, `${i}`));
  assert.equal(sampleAlias(table, 0.999999, 0), 4, 'a draw below the kept probability keeps its column');
  for (let i = 0; i < 100; i += 1) {
    for (let j = 0; j < 100; j += 1) assert.notEqual(sampleAlias(table, i / 100, j / 100), 2, 'a zero weight is never drawn');
  }
});

test('areas set the share of samples: 3 to 1 within five standard deviations', () => {
  const samples = scatterOnSurface(TWO, null, {count: 40000, seed: 4});
  let large = 0;
  for (const triangle of samples.triangles) large += triangle;
  // Binomial(40000, 0.75): mean 30000, standard deviation sqrt(40000 * 0.75 * 0.25) = 86.6.
  assert.ok(Math.abs(large - 30000) < 5 * 86.6, `${large} samples on the larger triangle`);
});

test('every sample lies on its triangle with valid barycentrics and a unit normal', () => {
  const indexed = Uint16Array.from([0, 1, 2, 3, 4, 5]);
  const samples = scatterOnSurface(TWO, indexed, {count: 2000, seed: 9});
  for (let k = 0; k < 2000; k += 1) {
    const [a, b, c] = samples.barycentrics.subarray(3 * k, 3 * k + 3);
    assert.ok(a >= -1e-7 && b >= -1e-7 && c >= -1e-7 && Math.abs(a + b + c - 1) < 1e-6);
    const t = samples.triangles[k];
    for (let axis = 0; axis < 3; axis += 1) {
      const expected = a * TWO[(3 * t) * 3 + axis] + b * TWO[(3 * t + 1) * 3 + axis] + c * TWO[(3 * t + 2) * 3 + axis];
      assert.ok(Math.abs(samples.positions[3 * k + axis] - expected) < 1e-5);
    }
    assert.deepEqual(Array.from(samples.normals.subarray(3 * k, 3 * k + 3)), [0, 0, 1], 'counter-clockwise faces +z');
  }
});

test('points are uniform inside a triangle; known wrong: the sampler without the square root is refused', () => {
  const one = Float32Array.from([0, 0, 0, 4, 0, 0, 1, 3, 0]);
  const samples = scatterOnSurface(one, null, {count: 20000, seed: 12});
  // Chi-square with 3 degrees of freedom stays under 16.27 with probability 0.999.
  assert.ok(quarterChiSquare(samples.barycentrics) < 16.27);
  let state = 99;
  const next = () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
  const wrong = new Float32Array(3 * 20000);
  for (let k = 0; k < 20000; k += 1) {
    const root = next();
    const second = next();
    wrong.set([1 - root, root * (1 - second), root * second], 3 * k);
  }
  assert.ok(quarterChiSquare(wrong) > 100, 'the biased sampler crowds the first corner');
});

test('per-vertex weights shape the density: weight on one corner moves the mean barycentric to 1/2', () => {
  const one = Float32Array.from([0, 0, 0, 1, 0, 0, 0, 1, 0]);
  const samples = scatterOnSurface(one, null, {count: 20000, seed: 3, weights: Float32Array.from([1, 0, 0])});
  let mean = 0;
  for (let k = 0; k < 20000; k += 1) mean += samples.barycentrics[3 * k] / 20000;
  // Density proportional to b0 over a uniform triangle: E[b0^2] / E[b0] = (1/6) / (1/3) = 1/2, standard error 0.0016.
  assert.ok(Math.abs(mean - 0.5) < 0.01, `mean ${mean}`);
  const blocked = scatterOnSurface(TWO, null, {count: 500, seed: 3, weights: Float32Array.from([0, 0, 0, 1, 1, 1])});
  assert.ok(blocked.triangles.every((triangle) => triangle === 1), 'a zero-weight triangle gets nothing');
});

test('interpolated normals, geometry input and surface matrices', () => {
  const normals = Float32Array.from([0, 0, 1, 0, 0, 1, 0, 1, 0]);
  const samples = scatterOnSurface(TWO.subarray(0, 9), null, {count: 200, seed: 1, normals});
  for (let k = 0; k < 200; k += 1) assert.ok(Math.abs(Math.hypot(...samples.normals.subarray(3 * k, 3 * k + 3)) - 1) < 1e-6);
  const geometry = {
    attributes: {position: {array: TWO, itemSize: 3, count: 6}, normal: undefined},
    index: {array: Uint16Array.from([0, 1, 2, 3, 4, 5])},
  };
  const fromGeometry = scatterOnGeometry(geometry, {count: 300, seed: 2});
  assert.deepEqual(Array.from(fromGeometry.positions), Array.from(scatterOnSurface(TWO, geometry.index.array,
    {count: 300, seed: 2}).positions));
  const placed = {positions: Float32Array.from([1, 2, 3, 0, 0, 0]), normals: Float32Array.from([1, 0, 0, 0, -1, 0])};
  const matrices = surfaceMatrices(placed, {offset: 0.5, scale: 2, seed: 4});
  const up = [matrices[4], matrices[5], matrices[6]];
  assert.ok(Math.abs(up[0] - 2) < 1e-6 && Math.abs(up[1]) < 1e-6 && Math.abs(up[2]) < 1e-6, 'model +Y follows the normal');
  assert.deepEqual([matrices[12], matrices[13], matrices[14]], [1.5, 2, 3]);
  assert.ok(Math.abs(matrices[16 + 5] + 2) < 1e-6, 'a downward normal turns the model upside down');
  assert.equal(SURFACE_SCATTER_DEFAULTS.count, 1000);
  assert.equal(SURFACE_MATRIX_DEFAULTS.spin, true);
});

test('known wrong: invalid meshes and options are refused', () => {
  assert.throws(() => triangleAreas(Float32Array.from([0, 0, 0, 1])), RangeError);
  assert.throws(() => scatterOnSurface(TWO, Uint16Array.from([0, 1, 9])), RangeError);
  assert.throws(() => scatterOnSurface(Float32Array.from([0, 0, 0, 0, 0, 0, 0, 0, 0])), RangeError);
  assert.throws(() => buildAliasTable([1, -1]), RangeError);
  assert.throws(() => scatterOnSurface(TWO, null, {count: -1}), RangeError);
  assert.throws(() => scatterOnSurface(TWO, null, {amount: 4}), TypeError);
  assert.throws(() => scatterOnSurface(TWO, null, {toString: 1}), TypeError, 'an inherited name is not an option');
  const upward = {attributes: {position: {array: TWO.subarray(0, 9), itemSize: 3, count: 3},
    normal: {array: Float32Array.from([0, 1, 0, 0, 1, 0, 0, 1, 0]), itemSize: 3, count: 3}}, index: null};
  const inherited = scatterOnGeometry(upward, Object.create({normals: null}));
  assert.deepEqual(Array.from(inherited.normals.subarray(0, 3)), [0, 1, 0], 'an inherited normals option is ignored');
  assert.throws(() => surfaceMatrices({positions: new Float32Array(3), normals: new Float32Array(3)}, {constructor: 1}), TypeError);
  assert.throws(() => scatterOnSurface(TWO, null, {weights: Float32Array.from([1, 2])}), RangeError);
  assert.throws(() => surfaceMatrices({positions: new Float32Array(3), normals: new Float32Array(6)}), RangeError);
});
