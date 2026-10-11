// FABRIK (forward and backward reaching inverse kinematics) for a chain of any number of joints with a fixed root:
// alternately pull the chain's end onto the target and its root back to the base, keeping every segment length,
// until the end is within tolerance or the iteration cap is reached; a target out of reach straightens the chain
// toward it. Original Baltor implementation; joints are [x, y, z] arrays, and only applyFabrikChain needs three.js,
// passed in as THREE.

/** Default options: the end-to-target distance that counts as reached, and the iteration cap. */
export const FABRIK_DEFAULTS = Object.freeze({tolerance: 1e-4, maxIterations: 32});

const TINY = 1e-12;

function vector(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be three finite numbers`);
  }
  return value;
}

function distance(a, b) { return Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]); }

// The point at `reach` from `from` on the way to `toward` (toward itself when they coincide is not allowed: the
// fallback direction keeps the segment length).
function along(from, toward, reach, fallback) {
  const span = distance(from, toward);
  if (span < TINY) return [from[0] + fallback[0] * reach, from[1] + fallback[1] * reach, from[2] + fallback[2] * reach];
  const ratio = reach / span;
  return [from[0] + (toward[0] - from[0]) * ratio, from[1] + (toward[1] - from[1]) * ratio, from[2] + (toward[2] - from[2]) * ratio];
}

/** The segment lengths of a chain of joints; every segment must have a non-zero length. */
export function chainLengths(joints) {
  if (!Array.isArray(joints) || joints.length < 2) throw new TypeError('a chain needs at least two joints');
  joints.forEach((joint, index) => vector(joint, `joints[${index}]`));
  const lengths = [];
  for (let index = 0; index < joints.length - 1; index += 1) {
    const span = distance(joints[index], joints[index + 1]);
    if (!(span > 0)) throw new RangeError(`segment ${index} has zero length`);
    lengths.push(span);
  }
  return lengths;
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(FABRIK_DEFAULTS, key)) throw new TypeError(`unknown FABRIK option ${key}`);
  }
  const settings = {...FABRIK_DEFAULTS, ...options};
  if (!(settings.tolerance > 0 && settings.tolerance < 1e6)) throw new RangeError('tolerance must be positive');
  if (!(Number.isInteger(settings.maxIterations) && settings.maxIterations >= 1 && settings.maxIterations <= 10000)) {
    throw new RangeError('maxIterations must be an integer from 1 to 10000');
  }
  return settings;
}

/**
 * The distances from the root a chain's end can reach: from max(0, longest segment - the sum of the others) to the
 * sum of all segments.
 */
export function chainReach(joints) {
  const lengths = chainLengths(joints);
  const total = lengths.reduce((sum, value) => sum + value, 0);
  return {shortest: Math.max(0, 2 * Math.max(...lengths) - total), longest: total};
}

/**
 * Solve the chain for a target, starting from the given pose (so last frame's answer is a good start). Returns
 * {joints, iterations, error, reached, reachable}: new joint positions with the root unchanged, the passes made,
 * the end's distance from the target, whether that is within tolerance, and whether the target's distance from the
 * root lies within chainReach. A target too close to the root still runs the passes and folds the chain as far as
 * the passes take it; near either end of the reach the passes converge slowly.
 */
export function solveFabrik(joints, target, options = {}) {
  const settings = settingsOf(options);
  const lengths = chainLengths(joints);
  vector(target, 'target');
  const base = [...joints[0]];
  const total = lengths.reduce((sum, value) => sum + value, 0);
  const shortest = Math.max(0, 2 * Math.max(...lengths) - total);
  const points = joints.map((joint) => [...joint]);
  const last = points.length - 1;
  const fallback = [0, 1, 0];
  if (distance(base, target) >= total) {
    for (let index = 0; index < last; index += 1) points[index + 1] = along(points[index], target, lengths[index], fallback);
    return {joints: points, iterations: 0, error: distance(points[last], target), reached: false, reachable: false};
  }
  let iterations = 0;
  let error = distance(points[last], target);
  while (error > settings.tolerance && iterations < settings.maxIterations) {
    points[last] = [...target];
    for (let index = last - 1; index >= 0; index -= 1) points[index] = along(points[index + 1], points[index], lengths[index], fallback);
    points[0] = [...base];
    for (let index = 0; index < last; index += 1) points[index + 1] = along(points[index], points[index + 1], lengths[index], fallback);
    iterations += 1;
    error = distance(points[last], target);
  }
  return {joints: points, iterations, error, reached: error <= settings.tolerance, reachable: distance(base, target) >= shortest};
}

function rotationBetween(from, to) {
  const a = Math.hypot(...from);
  const b = Math.hypot(...to);
  const u = from.map((value) => value / a);
  const v = to.map((value) => value / b);
  const cosine = u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
  if (cosine < -1 + 1e-12) {
    const helper = Math.abs(u[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0];
    const axis = [u[1] * helper[2] - u[2] * helper[1], u[2] * helper[0] - u[0] * helper[2], u[0] * helper[1] - u[1] * helper[0]];
    const size = Math.hypot(...axis);
    return [axis[0] / size, axis[1] / size, axis[2] / size, 0];
  }
  const q = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0], 1 + cosine];
  const norm = Math.hypot(...q);
  return q.map((value) => value / norm);
}

/**
 * Pose a three.js chain (objects[i + 1] a descendant of objects[i]; bones or any Object3D) so its last object
 * reaches `target`, a world position as an array. Each object except the last is rotated about its own origin by
 * the shortest arc that turns its segment onto the solved one, from the root outward. Returns the solveFabrik
 * result. Assumes uniform scale on the chain and its parents.
 */
export function applyFabrikChain(THREE, objects, target, options = {}) {
  if (!Array.isArray(objects) || objects.length < 2
    || !objects.every((object) => object && typeof object.getWorldPosition === 'function')) {
    throw new TypeError('objects must be at least two three.js Object3D joints, root first');
  }
  objects[0].updateWorldMatrix(true, true);
  const position = (object) => object.getWorldPosition(new THREE.Vector3()).toArray();
  const solution = solveFabrik(objects.map(position), target, options);
  for (let index = 0; index < objects.length - 1; index += 1) {
    const from = position(objects[index]);
    const to = position(objects[index + 1]);
    const want = solution.joints;
    const turn = rotationBetween([to[0] - from[0], to[1] - from[1], to[2] - from[2]],
      [want[index + 1][0] - want[index][0], want[index + 1][1] - want[index][1], want[index + 1][2] - want[index][2]]);
    const object = objects[index];
    const world = object.getWorldQuaternion(new THREE.Quaternion());
    const turned = new THREE.Quaternion(turn[0], turn[1], turn[2], turn[3]).multiply(world);
    const parent = object.parent ? object.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
    object.quaternion.copy(parent.invert().multiply(turned));
    object.updateMatrixWorld(true);
  }
  return solution;
}
