// Known answers for frustum culling: the planes of a 90 degree perspective matrix, sphere and box classification,
// agreement with the clip-space test -w <= x, y, z <= w for thousands of random points and a moved camera,
// WebGPU-style depth, and instance compaction with scale and in-place copies. Planes read from the transposed matrix
// and unnormalized planes are the known-wrong controls.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FRUSTUM_CULL_DEFAULTS, FRUSTUM_RESULT, classifyBox, classifySphere, cullInstances, frustumPlanes, multiplyMatrices,
} from './frustum_instance_culling.mjs';

// A WebGL perspective matrix (column-major) built from its definition, and a view matrix for a camera at eye looking
// at target with +Y up: the inverse of the camera's rigid transform.
function perspective(fovDegrees, aspect, near, far, zeroToOne = false) {
  const f = 1 / Math.tan((fovDegrees * Math.PI) / 360);
  const m = new Array(16).fill(0);
  m[0] = f / aspect;
  m[5] = f;
  m[10] = zeroToOne ? far / (near - far) : (far + near) / (near - far);
  m[11] = -1;
  m[14] = zeroToOne ? (far * near) / (near - far) : (2 * far * near) / (near - far);
  return m;
}

function lookAtView(eye, target) {
  const back = eye.map((value, k) => value - target[k]);
  const length = Math.hypot(...back);
  const z = back.map((value) => value / length);
  const xRaw = [z[2], 0, -z[0]];
  const xLength = Math.hypot(...xRaw);
  const x = xRaw.map((value) => value / xLength);
  const y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]];
  const dot = (axis) => axis[0] * eye[0] + axis[1] * eye[1] + axis[2] * eye[2];
  return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x), -dot(y), -dot(z), 1];
}

function clipInside(matrix, point, zeroToOne = false) {
  const [x, y, z] = point;
  const clip = [0, 1, 2, 3].map((row) => matrix[row] * x + matrix[4 + row] * y + matrix[8 + row] * z + matrix[12 + row]);
  const low = zeroToOne ? 0 : -clip[3];
  return Math.abs(clip[0]) <= clip[3] && Math.abs(clip[1]) <= clip[3] && clip[2] >= low && clip[2] <= clip[3];
}

// Points where the plane test and the clip-space test disagree.
function disagreements(planes, matrix, zeroToOne = false) {
  let state = 2024;
  const next = () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
  const wrong = [];
  for (let k = 0; k < 4000; k += 1) {
    const point = [next() * 30 - 15, next() * 30 - 15, next() * 30 - 22];
    const inside = classifySphere(planes, point[0], point[1], point[2], 0) !== FRUSTUM_RESULT.OUTSIDE;
    if (inside !== clipInside(matrix, point, zeroToOne)) wrong.push(point);
  }
  return wrong;
}

const PROJECTION = perspective(90, 1, 1, 10);

test('the planes of a 90 degree frustum are the known planes', () => {
  const planes = frustumPlanes(PROJECTION);
  const half = Math.SQRT1_2;
  const expected = [[half, 0, -half, 0], [-half, 0, -half, 0], [0, half, -half, 0], [0, -half, -half, 0],
    [0, 0, -1, -1], [0, 0, 1, 10]];
  expected.forEach((plane, index) => plane.forEach((value, k) => {
    assert.ok(Math.abs(planes[index * 4 + k] - value) < 1e-12, `plane ${index} component ${k}`);
  }));
});

test('spheres and boxes are classified', () => {
  const planes = frustumPlanes(PROJECTION);
  assert.equal(classifySphere(planes, 0, 0, -5, 1), FRUSTUM_RESULT.INSIDE);
  assert.equal(classifySphere(planes, 0, 0, -0.5, 0.2), FRUSTUM_RESULT.OUTSIDE);
  assert.equal(classifySphere(planes, 0, 0, -1, 0.5), FRUSTUM_RESULT.INTERSECTS);
  assert.equal(classifySphere(planes, 100, 0, -5, 1), FRUSTUM_RESULT.OUTSIDE);
  assert.equal(classifySphere(planes, 4.9, 0, -5, 0.5), FRUSTUM_RESULT.INTERSECTS);
  assert.equal(classifySphere(planes, 0, 0, -10.6, 0.5), FRUSTUM_RESULT.OUTSIDE);
  assert.equal(classifyBox(planes, [-1, -1, -6], [1, 1, -4]), FRUSTUM_RESULT.INSIDE);
  assert.equal(classifyBox(planes, [-1, -1, -1.5], [1, 1, -0.5]), FRUSTUM_RESULT.INTERSECTS);
  assert.equal(classifyBox(planes, [-1, -1, 1], [1, 1, 3]), FRUSTUM_RESULT.OUTSIDE);
});

test('plane tests agree with the clip-space test for a moved camera and WebGPU depth', () => {
  const view = lookAtView([3, 2, 4], [0, 0, -6]);
  const matrix = multiplyMatrices(perspective(60, 1.6, 0.5, 30), view);
  assert.deepEqual(disagreements(frustumPlanes(matrix), matrix), []);
  const webgpu = multiplyMatrices(perspective(70, 1, 1, 12, true), view);
  assert.deepEqual(disagreements(frustumPlanes(webgpu, {depthZeroToOne: true}), webgpu, true), []);
  const near = frustumPlanes(perspective(90, 1, 1, 10, true), {depthZeroToOne: true}).subarray(16, 20);
  assert.ok([0, 0, -1, -1].every((value, k) => Math.abs(near[k] - value) < 1e-12), 'the same near plane at z = -1');
});

test('known wrong: transposed planes disagree and unnormalized planes misjudge a sphere', () => {
  const view = lookAtView([3, 2, 4], [0, 0, -6]);
  const matrix = Array.from(multiplyMatrices(perspective(60, 1.6, 0.5, 30), view));
  const transposed = matrix.map((_, k) => matrix[(k % 4) * 4 + Math.floor(k / 4)]);
  assert.ok(disagreements(frustumPlanes(transposed), matrix).length > 100);
  const planes = frustumPlanes(PROJECTION);
  assert.equal(classifySphere(planes, -4.5, 0, -5, 0.4), FRUSTUM_RESULT.INTERSECTS);
  const unnormalized = Float64Array.from(planes);
  for (let k = 0; k < 4; k += 1) unnormalized[k] *= Math.SQRT2;
  assert.equal(classifySphere(unnormalized, -4.5, 0, -5, 0.4), FRUSTUM_RESULT.INSIDE, 'the wrong answer');
});

test('cullInstances keeps visible instances in order, scales radii and compacts in place', () => {
  const planes = frustumPlanes(PROJECTION);
  const at = (x, y, z, scale = 1) => [scale, 0, 0, 0, 0, scale, 0, 0, 0, 0, scale, 0, x, y, z, 1];
  const source = Float32Array.from([...at(0, 0, -5), ...at(0, 0, 5), ...at(6, 0, -5), ...at(6, 0, -5, 3),
    ...at(-2, 1, -8)]);
  const target = new Float32Array(source.length);
  const indices = new Uint32Array(5);
  const kept = cullInstances(source, 0.5, planes, target, {indices});
  assert.equal(kept, 3);
  assert.deepEqual(Array.from(indices.subarray(0, 3)), [0, 3, 4], 'the scaled copy of the edge instance reaches in');
  assert.deepEqual(Array.from(target.subarray(16, 32)), Array.from(source.subarray(48, 64)));
  const inPlace = Float32Array.from(source);
  assert.equal(cullInstances(inPlace, 0.5, planes, inPlace), 3);
  assert.deepEqual(Array.from(inPlace.subarray(0, 48)), Array.from(target.subarray(0, 48)));
  const offCentre = cullInstances(Float32Array.from(at(6, 0, -5)), 0.5, planes, new Float32Array(16),
    {center: [-1, 0, 0]});
  assert.equal(offCentre, 1, 'a bounding sphere centred off the origin moves with the instance');
  assert.deepEqual([...FRUSTUM_CULL_DEFAULTS.center], [0, 0, 0]);
});

test('known wrong: malformed inputs and options are refused', () => {
  assert.throws(() => frustumPlanes([1, 2, 3]), RangeError);
  assert.throws(() => frustumPlanes(new Array(16).fill(0)), RangeError);
  assert.throws(() => frustumPlanes(PROJECTION, {reversedDepth: true}), TypeError);
  assert.throws(() => frustumPlanes(PROJECTION, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => multiplyMatrices(PROJECTION, [Number.NaN, ...PROJECTION.slice(1)]), RangeError);
  const planes = frustumPlanes(PROJECTION);
  assert.throws(() => cullInstances(new Float32Array(15), 1, planes, new Float32Array(16)), RangeError);
  assert.throws(() => cullInstances(new Float32Array(16), -1, planes, new Float32Array(16)), RangeError);
  assert.throws(() => cullInstances(new Float32Array(16), 1, planes, new Float32Array(16), {centre: [0, 0, 0]}), TypeError);
});
