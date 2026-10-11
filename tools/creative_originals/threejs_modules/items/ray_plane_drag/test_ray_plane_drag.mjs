// Known answers for pointer rays and plane dragging: pointer to NDC, the matrix inverse against closed-form inverses
// of perspective and orthographic projections, rays for both camera kinds and a camera looking straight down,
// ray-plane distances, and the drag controller's grab offset, misses and grid snapping. A ray left in view space
// (the camera's world matrix ignored) is the known-wrong control the ray check must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PLANE_DRAG_DEFAULTS, PlaneDrag, intersectRayPlane, invertMatrix, ndcFromPointer, planeFromNormalAndPoint, rayFromCamera,
} from './ray_plane_drag.mjs';

const IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
// Column-major WebGL projections and their inverses written from the projection equations.
function perspective(fovDegrees, aspect, near, far) {
  const f = 1 / Math.tan((fovDegrees * Math.PI) / 360);
  const a = (far + near) / (near - far);
  const b = (2 * far * near) / (near - far);
  return {
    matrix: [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, a, -1, 0, 0, b, 0],
    inverse: [aspect / f, 0, 0, 0, 0, 1 / f, 0, 0, 0, 0, 0, 1 / b, 0, 0, -1, a / b],
  };
}
const ORTHOGRAPHIC_INVERSE = [2, 0, 0, 0, 0, 1, 0, 0, 0, 0, -4.95, 0, 0, 0, -5.05, 1];
// A camera at (0, 5, 0) looking straight down (-Y), its up vector along world -Z.
const LOOKING_DOWN = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 5, 0, 1];

function close(actual, expected, tolerance = 1e-12) {
  return actual.length === expected.length && actual.every((value, k) => Math.abs(value - expected[k]) <= tolerance);
}

// Problems with a candidate ray function against directions and origins known from the camera geometry.
function rayProblems(ray) {
  const problems = [];
  const {inverse} = perspective(90, 2, 0.5, 50);
  for (const [x, y] of [[0, 0], [1, 0.5], [-0.25, -1]]) {
    const raw = [2 * x, y, -1];
    const length = Math.hypot(...raw);
    const got = ray(x, y, inverse, IDENTITY);
    if (!close(got.direction, raw.map((value) => value / length), 1e-12)) problems.push(`direction at ${x}, ${y}`);
  }
  const down = ray(0, 0, inverse, LOOKING_DOWN);
  if (!close(down.direction, [0, -1, 0]) || !close(down.origin, [0, 4.5, 0])) problems.push('the moved camera');
  const flat = ray(0.5, -0.5, ORTHOGRAPHIC_INVERSE, IDENTITY);
  if (!close(flat.origin, [1, -0.5, -0.1]) || !close(flat.direction, [0, 0, -1])) problems.push('the orthographic camera');
  return problems;
}

test('pointer positions become normalized device coordinates', () => {
  const rect = {left: 10, top: 20, width: 200, height: 100};
  assert.deepEqual(ndcFromPointer(110, 70, rect), [0, 0]);
  assert.deepEqual(ndcFromPointer(10, 20, rect), [-1, 1]);
  assert.deepEqual(ndcFromPointer(210, 120, rect), [1, -1]);
  assert.throws(() => ndcFromPointer(0, 0, {left: 0, top: 0, width: 0, height: 10}), RangeError);
});

test('invertMatrix matches the closed-form inverses of both projections', () => {
  const {matrix, inverse} = perspective(70, 1.5, 0.1, 100);
  assert.ok(close(Array.from(invertMatrix(matrix)), inverse, 1e-9));
  const orthographic = [0.5, 0, 0, 0, 0, 1, 0, 0, 0, 0, -2 / 9.9, 0, 0, 0, -10.1 / 9.9, 1];
  assert.ok(close(Array.from(invertMatrix(orthographic)), ORTHOGRAPHIC_INVERSE, 1e-9));
  assert.ok(close(Array.from(invertMatrix(LOOKING_DOWN)), [1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, -5, 1], 1e-12));
  assert.throws(() => invertMatrix(new Array(16).fill(1)), RangeError);
});

test('rays point where the camera geometry says, for perspective, orthographic and moved cameras', () => {
  assert.deepEqual(rayProblems(rayFromCamera), []);
  const nearPoint = rayFromCamera(0, 0, perspective(90, 1, 1, 10).inverse, IDENTITY, -1);
  assert.ok(close(nearPoint.origin, [0, 0, -1]), 'depth -1 unprojects to the near plane of a WebGL matrix');
});

test('known wrong: a ray left in view space is refused', () => {
  const viewSpace = (x, y, inverse) => rayFromCamera(x, y, inverse, IDENTITY);
  assert.notDeepEqual(rayProblems(viewSpace), []);
});

test('rays meet planes at the right distance, and miss parallel or receding planes', () => {
  assert.equal(intersectRayPlane([0, 5, 0], [0, -1, 0], [0, 1, 0], 0), 5);
  assert.equal(intersectRayPlane([0, 5, 0], [1, 0, 0], [0, 1, 0], 0), null);
  assert.equal(intersectRayPlane([0, 5, 0], [0, 1, 0], [0, 1, 0], 0), null);
  const plane = planeFromNormalAndPoint([0, 2, 0], [3, 1.5, -2]);
  assert.deepEqual(plane, {normal: [0, 1, 0], constant: -1.5});
  assert.equal(intersectRayPlane([3, 4, 0], [0, -1, 0], plane.normal, plane.constant), 2.5);
});

test('PlaneDrag keeps the grab offset, snaps in the plane and reports misses', () => {
  const drag = new PlaneDrag();
  const down = (x, z) => ({origin: [x, 10, z], direction: [0, -1, 0]});
  assert.equal(drag.move(down(0, 0)), null, 'nothing moves before begin');
  assert.equal(drag.begin(down(1, 1), [2, 0.5, 3]), true);
  assert.equal(drag.active, true);
  assert.deepEqual(drag.move(down(4, -2)), [5, 0.5, 0]);
  assert.equal(drag.move({origin: [0, 10, 0], direction: [1, 0, 0]}), null, 'a ray parallel to the plane misses');
  drag.end();
  assert.equal(drag.active, false);
  const snapping = new PlaneDrag({snap: 1});
  snapping.begin(down(1, 1), [2, 0.5, 3]);
  const snapped = snapping.move(down(4.3, -1.6));
  assert.ok(close(snapped, [5, 0.5, 0], 1e-12), `snapped to ${snapped}`);
  const tilted = new PlaneDrag({normal: [0, 1, 1], constant: 0, snap: 0.5});
  tilted.begin({origin: [0.2, 5, 5], direction: [0, -Math.SQRT1_2, -Math.SQRT1_2]}, [0.2, 0.3, 0.1]);
  const moved = tilted.move({origin: [1.37, 4, 4.4], direction: [0, -Math.SQRT1_2, -Math.SQRT1_2]});
  const height = (point) => (point[1] + point[2]) / Math.SQRT2;
  assert.ok(Math.abs(height(moved) - height([0.2, 0.3, 0.1])) < 1e-12, 'the height above the plane is kept');
  assert.ok(Math.abs(moved[0] / 0.5 - Math.round(moved[0] / 0.5)) < 1e-9, 'x lands on the grid');
  assert.deepEqual([...PLANE_DRAG_DEFAULTS.normal], [0, 1, 0]);
});

test('known wrong: invalid planes, rays and options are refused', () => {
  assert.throws(() => new PlaneDrag({normal: [0, 0, 0]}), RangeError);
  assert.throws(() => new PlaneDrag({snap: -1}), RangeError);
  assert.throws(() => new PlaneDrag({grid: 1}), TypeError);
  assert.throws(() => new PlaneDrag({toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => rayFromCamera(0, 0, [1, 2], IDENTITY), RangeError);
  assert.throws(() => rayFromCamera(0, 0, IDENTITY, IDENTITY, 0.5), RangeError);
  assert.throws(() => intersectRayPlane([0, 0], [0, 1, 0], [0, 1, 0], 0), RangeError);
});
