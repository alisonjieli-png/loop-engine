// Analytic two-bone inverse kinematics (an arm or a leg): from the root, mid and end joint positions, a target and a
// pole, place the mid joint by the law of cosines in the plane that holds the target and leans toward the pole, so
// the end reaches the target exactly when it can and the chain straightens toward it when it cannot. Original Baltor
// implementation; positions are [x, y, z] arrays, rotations quaternions [x, y, z, w]; only applyTwoBoneIK needs
// three.js, passed in as THREE.

/** Default options. reachMargin keeps the chain this fraction short of full extension (0 allows a straight chain). */
export const TWO_BONE_IK_DEFAULTS = Object.freeze({reachMargin: 0});

const TINY = 1e-12;

function vector(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be three finite numbers`);
  }
  return value;
}

function subtract(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
function scale(a, s) { return [a[0] * s, a[1] * s, a[2] * s]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function length(a) { return Math.hypot(a[0], a[1], a[2]); }
function normalize(a) { const size = length(a); return scale(a, 1 / size); }

function perpendicular(direction, preferred) {
  const lean = subtract(preferred, scale(direction, dot(preferred, direction)));
  return length(lean) > TINY * Math.max(1, length(preferred)) ? normalize(lean) : null;
}

/**
 * The shortest-arc rotation [x, y, z, w] that turns the direction of `from` into the direction of `to`. Opposite
 * directions give a half turn about an axis perpendicular to both.
 */
export function rotationBetween(from, to) {
  vector(from, 'from');
  vector(to, 'to');
  const a = length(from);
  const b = length(to);
  if (!(a > 0 && b > 0)) throw new RangeError('rotationBetween needs two non-zero vectors');
  const u = scale(from, 1 / a);
  const v = scale(to, 1 / b);
  const cosine = dot(u, v);
  if (cosine < -1 + 1e-12) {
    const axis = perpendicular(u, Math.abs(u[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]);
    return [axis[0], axis[1], axis[2], 0];
  }
  const axis = cross(u, v);
  const q = [axis[0], axis[1], axis[2], 1 + cosine];
  const norm = Math.hypot(q[0], q[1], q[2], q[3]);
  return q.map((value) => value / norm);
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(TWO_BONE_IK_DEFAULTS, key)) throw new TypeError(`unknown two-bone IK option ${key}`);
  }
  const settings = {...TWO_BONE_IK_DEFAULTS, ...options};
  if (!(settings.reachMargin >= 0 && settings.reachMargin < 0.5)) throw new RangeError('reachMargin must be in [0, 0.5)');
  return settings;
}

/**
 * Solve the chain root -> mid -> end for a target, bending toward the pole. Returns the new joint positions, the
 * world-space shortest-arc rotations that turn the upper bone (root to mid) and the lower bone (mid to end) from
 * their old directions to their new ones, whether the target was within reach, and the end's remaining distance.
 */
export function solveTwoBoneIK(root, mid, end, target, pole, options = {}) {
  [[root, 'root'], [mid, 'mid'], [end, 'end'], [target, 'target'], [pole, 'pole']].forEach(([value, name]) => vector(value, name));
  const settings = settingsOf(options);
  const upperLength = length(subtract(mid, root));
  const lowerLength = length(subtract(end, mid));
  if (!(upperLength > 0 && lowerLength > 0)) throw new RangeError('both bones need a non-zero length');
  const toTarget = subtract(target, root);
  const distance = length(toTarget);
  let direction;
  if (distance > TINY) direction = scale(toTarget, 1 / distance);
  else direction = length(subtract(end, root)) > TINY ? normalize(subtract(end, root)) : normalize(subtract(mid, root));
  const longest = (upperLength + lowerLength) * (1 - settings.reachMargin);
  const shortest = Math.abs(upperLength - lowerLength);
  const reach = Math.min(Math.max(distance, shortest), Math.max(longest, shortest));
  const bend = perpendicular(direction, subtract(pole, root))
    || perpendicular(direction, subtract(mid, root))
    || perpendicular(direction, Math.abs(direction[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]);
  let cosine = 0;
  if (reach > TINY) {
    cosine = (upperLength * upperLength + reach * reach - lowerLength * lowerLength) / (2 * upperLength * reach);
    cosine = Math.min(Math.max(cosine, -1), 1);
  }
  const sine = Math.sqrt(Math.max(0, 1 - cosine * cosine));
  const newMid = add(root, scale(add(scale(direction, cosine), scale(bend, sine)), upperLength));
  const newEnd = add(root, scale(direction, reach));
  const remaining = length(subtract(newEnd, target));
  return {
    root: [...root],
    mid: newMid,
    end: newEnd,
    rootRotation: rotationBetween(subtract(mid, root), subtract(newMid, root)),
    midRotation: rotationBetween(subtract(end, mid), subtract(newEnd, newMid)),
    reached: distance >= shortest - 1e-9 && distance <= longest + 1e-9,
    distance: remaining,
    upperLength,
    lowerLength,
  };
}

function rotateInWorld(THREE, object, rotation) {
  const world = object.getWorldQuaternion(new THREE.Quaternion());
  const turned = new THREE.Quaternion(rotation[0], rotation[1], rotation[2], rotation[3]).multiply(world);
  const parent = object.parent ? object.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
  object.quaternion.copy(parent.invert().multiply(turned));
  object.updateMatrixWorld(true);
}

/**
 * Pose a three.js hierarchy upper -> lower -> end (bones or any Object3D chain) so `end` reaches `target`, bending
 * toward `pole` (both world positions as arrays). The upper and lower objects are rotated about their own origins;
 * returns the solveTwoBoneIK result. Assumes uniform scale on the chain and its parents.
 */
export function applyTwoBoneIK(THREE, upper, lower, end, target, pole, options = {}) {
  for (const [object, name] of [[upper, 'upper'], [lower, 'lower'], [end, 'end']]) {
    if (!object || typeof object.getWorldPosition !== 'function') throw new TypeError(`${name} must be a three.js Object3D`);
  }
  upper.updateWorldMatrix(true, true);
  const position = (object) => object.getWorldPosition(new THREE.Vector3()).toArray();
  const solution = solveTwoBoneIK(position(upper), position(lower), position(end), target, pole, options);
  rotateInWorld(THREE, upper, solution.rootRotation);
  const lowerNow = position(lower);
  const endNow = position(end);
  rotateInWorld(THREE, lower, rotationBetween(subtract(endNow, lowerNow), subtract(solution.end, solution.mid)));
  return solution;
}
