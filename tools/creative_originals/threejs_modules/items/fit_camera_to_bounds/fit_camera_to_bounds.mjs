// Camera framing for three.js: the distance that fits a sphere in a perspective view (limited by the narrower of the
// vertical and horizontal fields of view), a tight perspective fit of a box from any view direction that brings at
// least one corner to the frame edge, an orthographic fit, near and far planes that bracket the box, and a helper
// that applies a fit to a camera. Original Baltor implementation; the fitting works on plain arrays.

/** Default options of the fit functions. direction is where the camera looks (from the camera toward the target). */
export const FIT_CAMERA_DEFAULTS = Object.freeze({
  direction: Object.freeze([0, 0, -1]),
  up: Object.freeze([0, 1, 0]),
  margin: 1,
  depthPadding: 1.05,
});

const DEGREES = Math.PI / 180;

function strict(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(FIT_CAMERA_DEFAULTS, key)) throw new TypeError(`unknown fit option ${key}`);
  }
  const settings = {...FIT_CAMERA_DEFAULTS, ...options};
  if (!(settings.margin >= 1 && Number.isFinite(settings.margin))) throw new RangeError('margin must be at least 1');
  if (!(settings.depthPadding >= 1 && Number.isFinite(settings.depthPadding))) {
    throw new RangeError('depthPadding must be at least 1');
  }
  return settings;
}

function checkFieldOfView(fovDegrees, aspect) {
  if (!(fovDegrees > 0 && fovDegrees < 180)) throw new RangeError('fovDegrees must be between 0 and 180');
  if (!(aspect > 0 && Number.isFinite(aspect))) throw new RangeError('aspect must be positive');
}

function checkVector(vector, name) {
  if (!(vector && vector.length === 3 && Array.prototype.every.call(vector, Number.isFinite))) {
    throw new RangeError(`${name} must be three finite numbers`);
  }
}

function basis(direction, up) {
  checkVector(direction, 'direction');
  checkVector(up, 'up');
  const length = Math.hypot(...direction);
  if (!(length > 0)) throw new RangeError('direction must not be zero');
  const forward = direction.map((value) => value / length);
  let right = [forward[1] * up[2] - forward[2] * up[1], forward[2] * up[0] - forward[0] * up[2],
    forward[0] * up[1] - forward[1] * up[0]];
  if (Math.hypot(...right) < 1e-9) {
    const other = Math.abs(forward[1]) < 0.9 ? [0, 1, 0] : [0, 0, -1];
    right = [forward[1] * other[2] - forward[2] * other[1], forward[2] * other[0] - forward[0] * other[2],
      forward[0] * other[1] - forward[1] * other[0]];
  }
  const rightLength = Math.hypot(...right);
  right = right.map((value) => value / rightLength);
  const upward = [right[1] * forward[2] - right[2] * forward[1], right[2] * forward[0] - right[0] * forward[2],
    right[0] * forward[1] - right[1] * forward[0]];
  return {forward, right, upward};
}

function corners(min, max) {
  checkVector(min, 'min');
  checkVector(max, 'max');
  if (!(min[0] <= max[0] && min[1] <= max[1] && min[2] <= max[2])) throw new RangeError('min must not exceed max');
  const list = [];
  for (let k = 0; k < 8; k += 1) list.push([k & 1 ? max[0] : min[0], k & 2 ? max[1] : min[1], k & 4 ? max[2] : min[2]]);
  return list;
}

// Each corner in the camera basis around the box centre: x right, y up, z further from the camera.
function cameraSpace(min, max, frame) {
  const centre = [0, 1, 2].map((axis) => (min[axis] + max[axis]) / 2);
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  return {
    centre,
    points: corners(min, max).map((point) => {
      const relative = point.map((value, axis) => value - centre[axis]);
      return [dot(relative, frame.right), dot(relative, frame.upward), dot(relative, frame.forward)];
    }),
  };
}

/**
 * The distance from a sphere's centre at which a perspective camera with vertical field fovDegrees and the given
 * aspect (width / height) just contains the sphere: radius / sin(half), half being the narrower half-angle.
 */
export function fitSphereDistance(radius, fovDegrees, aspect = 1) {
  checkFieldOfView(fovDegrees, aspect);
  if (!(radius >= 0 && Number.isFinite(radius))) throw new RangeError('radius must be a non-negative number');
  const halfVertical = (fovDegrees * DEGREES) / 2;
  const halfHorizontal = Math.atan(Math.tan(halfVertical) * aspect);
  return radius / Math.sin(Math.min(halfVertical, halfHorizontal));
}

/**
 * A perspective fit of the box [min, max] seen along options.direction: {position, target, up, distance, near, far}.
 * The camera looks at the box centre from the smallest distance at which every corner is inside the frame shrunk by
 * margin; with margin 1 at least one corner touches the frame edge. near and far bracket the box, widened by
 * depthPadding.
 */
export function fitBoxPerspective(min, max, fovDegrees, aspect, options = {}) {
  checkFieldOfView(fovDegrees, aspect);
  const settings = strict(options);
  const frame = basis(settings.direction, settings.up);
  const {centre, points} = cameraSpace(min, max, frame);
  const tanVertical = Math.tan((fovDegrees * DEGREES) / 2);
  const tanHorizontal = tanVertical * aspect;
  let distance = 0;
  let nearest = Infinity;
  let farthest = -Infinity;
  for (const [x, y, z] of points) {
    distance = Math.max(distance, (Math.abs(x) * settings.margin) / tanHorizontal - z,
      (Math.abs(y) * settings.margin) / tanVertical - z);
    nearest = Math.min(nearest, z);
    farthest = Math.max(farthest, z);
  }
  const size = Math.max(farthest - nearest, 1e-9);
  distance = Math.max(distance, -nearest + size * 1e-3);
  return {
    position: centre.map((value, axis) => value - frame.forward[axis] * distance),
    target: centre,
    up: frame.upward,
    distance,
    near: Math.max((distance + nearest) / settings.depthPadding, distance * 1e-5),
    far: (distance + farthest) * settings.depthPadding,
  };
}

/**
 * An orthographic fit of the box: {position, target, up, left, right, top, bottom, near, far}, a frustum of the
 * given aspect that contains every corner inside the frame shrunk by margin, the camera one box diagonal back.
 */
export function fitBoxOrthographic(min, max, aspect, options = {}) {
  if (!(aspect > 0 && Number.isFinite(aspect))) throw new RangeError('aspect must be positive');
  const settings = strict(options);
  const frame = basis(settings.direction, settings.up);
  const {centre, points} = cameraSpace(min, max, frame);
  let halfWidth = 0;
  let halfHeight = 0;
  let nearest = Infinity;
  let farthest = -Infinity;
  for (const [x, y, z] of points) {
    halfWidth = Math.max(halfWidth, Math.abs(x) * settings.margin);
    halfHeight = Math.max(halfHeight, Math.abs(y) * settings.margin);
    nearest = Math.min(nearest, z);
    farthest = Math.max(farthest, z);
  }
  if (halfWidth / Math.max(halfHeight, 1e-12) > aspect) halfHeight = halfWidth / aspect;
  else halfWidth = halfHeight * aspect;
  const diagonal = Math.max(Math.hypot(max[0] - min[0], max[1] - min[1], max[2] - min[2]), 1e-9);
  const back = diagonal;
  const pad = (farthest - nearest) * (settings.depthPadding - 1) + diagonal * 1e-3;
  return {
    position: centre.map((value, axis) => value - frame.forward[axis] * back),
    target: centre,
    up: frame.upward,
    left: -halfWidth,
    right: halfWidth,
    top: halfHeight,
    bottom: -halfHeight,
    near: Math.max(back + nearest - pad, 1e-6),
    far: back + farthest + pad,
  };
}

/**
 * Apply a fit to a three.js camera: position, up, lookAt the target, near and far, the orthographic extents when the
 * fit has them, zoom back to 1 (the fits assume it), then updateProjectionMatrix(). Returns the camera.
 */
export function applyFit(camera, fit) {
  camera.zoom = 1;
  camera.position.set(fit.position[0], fit.position[1], fit.position[2]);
  camera.up.set(fit.up[0], fit.up[1], fit.up[2]);
  camera.lookAt(fit.target[0], fit.target[1], fit.target[2]);
  camera.near = fit.near;
  camera.far = fit.far;
  if (Object.prototype.hasOwnProperty.call(fit, 'left')) {
    camera.left = fit.left;
    camera.right = fit.right;
    camera.top = fit.top;
    camera.bottom = fit.bottom;
  }
  camera.updateProjectionMatrix();
  return camera;
}
