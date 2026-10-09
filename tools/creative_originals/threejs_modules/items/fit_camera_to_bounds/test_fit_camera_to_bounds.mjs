// Known answers for camera framing: sphere distances in closed form (radius 1 at 90 degrees is sqrt(2), a portrait
// aspect of 0.5 gives sqrt(5)), and box fits checked by projecting all eight corners through a camera built in this
// test from the fit: inside the frame, one corner on the edge, depth inside near and far. A fitter that ignores the
// aspect ratio is the known-wrong control the projection check must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  FIT_CAMERA_DEFAULTS, applyFit, fitBoxOrthographic, fitBoxPerspective, fitSphereDistance,
} from './fit_camera_to_bounds.mjs';

function viewMatrix(position, target, up) {
  const back = position.map((value, k) => value - target[k]);
  const z = back.map((value) => value / Math.hypot(...back));
  const xRaw = [up[1] * z[2] - up[2] * z[1], up[2] * z[0] - up[0] * z[2], up[0] * z[1] - up[1] * z[0]];
  const x = xRaw.map((value) => value / Math.hypot(...xRaw));
  const y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]];
  const dot = (axis) => axis[0] * position[0] + axis[1] * position[1] + axis[2] * position[2];
  return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x), -dot(y), -dot(z), 1];
}

function project(matrix, point) {
  return [0, 1, 2, 3].map((row) => matrix[row] * point[0] + matrix[4 + row] * point[1] + matrix[8 + row] * point[2]
    + matrix[12 + row]);
}

function cornersOf(min, max) {
  return Array.from({length: 8}, (_, k) => [k & 1 ? max[0] : min[0], k & 2 ? max[1] : min[1], k & 4 ? max[2] : min[2]]);
}

// Problems with a fit: corners outside the frame or the depth range, or no corner on the frame edge.
function projectionProblems(fit, min, max, fov, aspect, margin, orthographic = false) {
  const view = viewMatrix(fit.position, fit.target, fit.up);
  const problems = [];
  let edge = 0;
  for (const corner of cornersOf(min, max)) {
    const [vx, vy, vz] = project(view, corner);
    let ndcX;
    let ndcY;
    if (orthographic) {
      ndcX = (2 * vx - (fit.right + fit.left)) / (fit.right - fit.left);
      ndcY = (2 * vy - (fit.top + fit.bottom)) / (fit.top - fit.bottom);
    } else {
      const tangent = Math.tan((fov * Math.PI) / 360);
      ndcX = vx / (-vz * tangent * aspect);
      ndcY = vy / (-vz * tangent);
    }
    if (Math.abs(ndcX) > 1 / margin + 1e-9 || Math.abs(ndcY) > 1 / margin + 1e-9) problems.push(`corner ${corner} leaves the frame`);
    if (!(-vz >= fit.near && -vz <= fit.far)) problems.push(`corner ${corner} is outside near and far`);
    edge = Math.max(edge, Math.abs(ndcX), Math.abs(ndcY));
  }
  if (Math.abs(edge - 1 / margin) > 1e-9) problems.push(`the outermost corner reaches ${edge}, not ${1 / margin}`);
  return problems;
}

test('sphere distances follow radius / sin of the narrower half-angle', () => {
  assert.ok(Math.abs(fitSphereDistance(1, 90, 1) - 1.4142135623730951) < 1e-12);
  assert.ok(Math.abs(fitSphereDistance(1, 90, 0.5) - 2.23606797749979) < 1e-12, 'portrait: the horizontal field binds');
  assert.ok(Math.abs(fitSphereDistance(1, 60, 2) - 2) < 1e-12, 'landscape: the vertical field binds');
  assert.ok(Math.abs(fitSphereDistance(2, 50, 0.75) - 6.058329762999929) < 1e-9);
  assert.equal(fitSphereDistance(0, 45, 1), 0);
});

test('perspective box fits put every corner inside and one on the edge', () => {
  const cases = [
    {min: [-1, -1, -1], max: [1, 1, 1], fov: 50, aspect: 1, options: {}},
    {min: [-3, 0, -0.5], max: [3, 1, 0.5], fov: 45, aspect: 0.6, options: {direction: [-1, -0.6, -1.2]}},
    {min: [2, -1, 4], max: [2.5, 6, 5], fov: 35, aspect: 1.8, options: {direction: [0.3, -0.2, -1], margin: 1.25}},
    {min: [-1, 0, -1], max: [1, 0.2, 1], fov: 60, aspect: 1.2, options: {direction: [0, -1, 0]}},
  ];
  for (const {min, max, fov, aspect, options} of cases) {
    const fit = fitBoxPerspective(min, max, fov, aspect, options);
    assert.deepEqual(projectionProblems(fit, min, max, fov, aspect, options.margin || 1), [], JSON.stringify(options));
    const back = fit.position.map((value, k) => fit.target[k] - value);
    assert.ok(Math.abs(Math.hypot(...back) - fit.distance) < 1e-9);
  }
});

test('orthographic box fits keep the aspect and touch the frame', () => {
  const min = [-3, 0, -0.5];
  const max = [3, 1, 0.5];
  for (const aspect of [0.5, 1, 2.5]) {
    const fit = fitBoxOrthographic(min, max, aspect, {direction: [-1, -0.6, -1.2]});
    assert.ok(Math.abs((fit.right - fit.left) / (fit.top - fit.bottom) - aspect) < 1e-12);
    assert.deepEqual(projectionProblems(fit, min, max, 0, aspect, 1, true), []);
  }
});

test('known wrong: a fitter that ignores the aspect ratio leaves corners outside a portrait frame', () => {
  const min = [-3, 0, -0.5];
  const max = [3, 1, 0.5];
  const ignoresAspect = fitBoxPerspective(min, max, 45, 1, {});
  assert.notDeepEqual(projectionProblems(ignoresAspect, min, max, 45, 0.6, 1), []);
});

test('applyFit sets position, up, target, depth range and extents on a camera', () => {
  const calls = [];
  const vector = (name) => ({set: (...values) => calls.push([name, ...values])});
  const camera = {position: vector('position'), up: vector('up'), zoom: 2, lookAt: (...values) => calls.push(['lookAt', ...values]),
    updateProjectionMatrix: () => calls.push(['update'])};
  const fit = fitBoxOrthographic([0, 0, 0], [1, 1, 1], 1);
  assert.equal(applyFit(camera, fit), camera);
  assert.deepEqual(calls.map((call) => call[0]), ['position', 'up', 'lookAt', 'update']);
  assert.deepEqual(calls[2].slice(1), [0.5, 0.5, 0.5]);
  assert.equal(camera.zoom, 1);
  assert.equal(camera.left, fit.left);
  assert.equal(camera.near, fit.near);
  assert.equal(FIT_CAMERA_DEFAULTS.margin, 1);
  const perspectiveCamera = {position: vector('position'), up: vector('up'), lookAt() {}, updateProjectionMatrix() {}};
  const inherits = Object.assign(Object.create({left: -9}), fitBoxPerspective([0, 0, 0], [1, 1, 1], 45, 1));
  applyFit(perspectiveCamera, inherits);
  assert.equal(perspectiveCamera.left, undefined, 'an inherited left is not an orthographic extent');
});

test('known wrong: invalid fields of view, boxes and options are refused', () => {
  assert.throws(() => fitSphereDistance(1, 0, 1), RangeError);
  assert.throws(() => fitSphereDistance(1, 180, 1), RangeError);
  assert.throws(() => fitSphereDistance(-1, 45, 1), RangeError);
  assert.throws(() => fitBoxPerspective([1, 0, 0], [0, 1, 1], 45, 1), RangeError);
  assert.throws(() => fitBoxPerspective([0, 0, 0], [1, 1, 1], 45, 1, {direction: [0, 0, 0]}), RangeError);
  assert.throws(() => fitBoxPerspective([0, 0, 0], [1, 1, 1], 45, 1, {margin: 0.5}), RangeError);
  assert.throws(() => fitBoxOrthographic([0, 0, 0], [1, 1, 1], 1, {padding: 2}), TypeError);
  assert.throws(() => fitBoxOrthographic([0, 0, 0], [1, 1, 1], 1, {toString: 1}), TypeError, 'an inherited name is not an option');
});
