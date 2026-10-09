// Known answers for the scene budget report, worked out by hand: the primitive counts of every mode, a translated
// triangle's world bounds, two instances of one mesh under a node turned 90 degrees about +Y (x maps to -z, z to x),
// node depth, texture memory with and without mip chains (256 x 256 x 4 bytes, times 4/3), and budget violations.
// Known-wrong controls: a mode table that counts strips as lists is refused, a node cycle throws, and a budget below
// the count reports a violation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {BUDGET_METRICS, REPORT_DEFAULTS, checkBudget, primitiveCounts, sceneBudgetReport} from './gltf_scene_budget_report.mjs';

const MODE_TABLE = [
  [0, 7, {triangles: 0, lines: 0, points: 7}],
  [1, 6, {triangles: 0, lines: 3, points: 0}],
  [2, 5, {triangles: 0, lines: 5, points: 0}],
  [3, 4, {triangles: 0, lines: 3, points: 0}],
  [4, 9, {triangles: 3, lines: 0, points: 0}],
  [5, 5, {triangles: 3, lines: 0, points: 0}],
  [6, 6, {triangles: 4, lines: 0, points: 0}],
];

function modeProblems(counts) {
  return MODE_TABLE.filter(([mode, count, expected]) => JSON.stringify(counts(mode, count)) !== JSON.stringify(expected))
    .map(([mode]) => `mode ${mode}`);
}

const TRIANGLE_ACCESSORS = [
  {componentType: 5126, count: 3, type: 'VEC3', min: [0, 0, 0], max: [1, 1, 0]},
  {componentType: 5123, count: 3, type: 'SCALAR'},
];

function document(nodes, roots, extra = {}) {
  return {
    asset: {version: '2.0'}, scene: 0, scenes: [{nodes: roots}], nodes,
    meshes: [{primitives: [{attributes: {POSITION: 0}, indices: 1, material: 0}]}],
    materials: [{pbrMetallicRoughness: {baseColorTexture: {index: 0}}}], textures: [{source: 0}], images: [{uri: 'a.png'}],
    accessors: TRIANGLE_ACCESSORS, ...extra,
  };
}

function close(actual, expected) {
  return actual.every((value, index) => Math.abs(value - expected[index]) < 1e-12);
}

test('primitiveCounts follows each primitive mode', () => {
  assert.deepEqual(modeProblems(primitiveCounts), []);
  assert.deepEqual(primitiveCounts(5, 1), {triangles: 0, lines: 0, points: 0});
  assert.throws(() => primitiveCounts(7, 3), RangeError);
  assert.throws(() => primitiveCounts(4, -1), RangeError);
});

test('known wrong: a mode table that counts strips and fans as lists is refused', () => {
  const wrong = (mode, count) => (mode >= 4 ? {triangles: Math.floor(count / 3), lines: 0, points: 0} : primitiveCounts(mode, count));
  assert.deepEqual(modeProblems(wrong), ['mode 5', 'mode 6']);
});

test('a translated triangle: counts and world bounds', () => {
  const report = sceneBudgetReport(document([{mesh: 0, translation: [0, 1, 0]}], [0]), {imageSizes: [{width: 256, height: 256}]});
  assert.equal(report.triangles, 1);
  assert.equal(report.vertices, 3);
  assert.equal(report.drawCalls, 1);
  assert.equal(report.maxDepth, 1);
  assert.deepEqual(report.bounds, {min: [0, 1, 0], max: [1, 2, 0]});
  assert.equal(report.extent, 1);
  assert.deepEqual([report.materials, report.textures, report.images], [1, 1, 1]);
  assert.equal(report.textureBytes, 349525, '256 * 256 * 4 * 4 / 3, rounded');
  const flat = sceneBudgetReport(document([{mesh: 0}], [0]), {imageSizes: [{width: 256, height: 256}], mipmaps: false});
  assert.equal(flat.textureBytes, 262144);
});

test('two instances under a quarter turn about +Y', () => {
  const half = Math.SQRT1_2;
  const nodes = [{rotation: [0, half, 0, half], children: [1, 2]}, {mesh: 0}, {mesh: 0, translation: [2, 0, 0]}];
  const report = sceneBudgetReport(document(nodes, [0]));
  assert.deepEqual([report.meshInstances, report.drawCalls, report.triangles, report.vertices], [2, 2, 2, 6]);
  assert.deepEqual([report.nodes, report.maxDepth], [3, 2]);
  assert.ok(close(report.bounds.min, [0, 0, -3]), JSON.stringify(report.bounds));
  assert.ok(close(report.bounds.max, [0, 1, 0]), JSON.stringify(report.bounds));
  assert.ok(Math.abs(report.extent - 3) < 1e-12);
  assert.equal(report.textureBytes, null, 'no image sizes were given');
  assert.deepEqual(report.unknownImageSizes, [0]);
  assert.deepEqual(report.modes, [0, 0, 0, 0, 2, 0, 0]);
});

test('a matrix node and a deep chain', () => {
  const matrix = [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 5, 0, 0, 1];
  const nodes = [{children: [1]}, {children: [2]}, {children: [3]}, {mesh: 0, matrix}];
  const report = sceneBudgetReport(document(nodes, [0]));
  assert.equal(report.maxDepth, 4);
  assert.deepEqual(report.bounds, {min: [5, 0, 0], max: [7, 2, 0]});
});

test('checkBudget lists what goes over and what is unknown', () => {
  const report = sceneBudgetReport(document([{mesh: 0}], [0]));
  assert.deepEqual(checkBudget(report, {triangles: 10, drawCalls: 4}), []);
  assert.deepEqual(checkBudget(report, {triangles: 0, textureBytes: 1000}), [
    {metric: 'triangles', value: 1, limit: 0, reason: 'over'},
    {metric: 'textureBytes', value: null, limit: 1000, reason: 'unknown'},
  ]);
  assert.throws(() => checkBudget(report, {polygons: 10}), TypeError);
  assert.throws(() => checkBudget(report, {triangles: -1}), RangeError);
  assert.ok(BUDGET_METRICS.includes('drawCalls'));
});

test('known wrong: a node cycle and bad options are refused', () => {
  assert.throws(() => sceneBudgetReport(document([{children: [1]}, {children: [0]}], [0])), RangeError);
  assert.throws(() => sceneBudgetReport(document([{mesh: 'toString'}], [0])), RangeError, 'an inherited name is not a mesh');
  assert.throws(() => sceneBudgetReport(document([{mesh: 0}], ['constructor'])), RangeError);
  assert.throws(() => sceneBudgetReport(document([{mesh: 0}], [0]), {scenes: 0}), TypeError);
  assert.throws(() => sceneBudgetReport(document([{mesh: 0}], [0]), {toString: 0}), TypeError, 'an inherited name is not an option');
  assert.throws(() => checkBudget({}, {toString: 1}), TypeError);
  assert.throws(() => sceneBudgetReport(document([{mesh: 0}], [0]), {scene: 4}), RangeError);
  assert.equal(REPORT_DEFAULTS.mipmaps, true);
  assert.equal(sceneBudgetReport({asset: {version: '2.0'}}).triangles, 0, 'a document without scenes draws nothing');
});
