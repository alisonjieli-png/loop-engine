// Cinematic camera path: a centripetal Catmull-Rom spline through keyframe positions, sampled at constant speed
// through an arc-length table, with the orientation taken from interpolated look targets, from slerped quaternion
// keyframes or from the direction of travel, and an easing curve on the timeline. Original Baltor implementation;
// plain arrays in and out ([x, y, z] and quaternions [x, y, z, w] for a camera that looks down -Z), nothing imported.

/** Default options of CameraPath. alpha 0 is the uniform, 0.5 the centripetal and 1 the chordal spline. */
export const CINEMATIC_PATH_DEFAULTS = Object.freeze({
  alpha: 0.5,
  closed: false,
  samplesPerSegment: 64,
  easing: 'smoothstep',
  up: Object.freeze([0, 1, 0]),
});

const EASINGS = new Set(['linear', 'smoothstep', 'smootherstep']);
const MINIMUM_KNOT = 1e-12;
const NEAR_PARALLEL = 1e-9;

function isVector(value, size) {
  return Array.isArray(value) && value.length === size && value.every(Number.isFinite);
}

function vector(value, name, size = 3) {
  if (!isVector(value, size)) throw new TypeError(`${name} must be ${size} finite numbers`);
  return value;
}

function subtract(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function length(a) { return Math.hypot(a[0], a[1], a[2]); }
function scale(a, s) { return [a[0] * s, a[1] * s, a[2] * s]; }

function knot(a, b, alpha) {
  return Math.max(length(subtract(b, a)) ** alpha, MINIMUM_KNOT);
}

/**
 * The point at local parameter u in [0, 1] on the Catmull-Rom segment from p1 to p2, with neighbours p0 and p3 and
 * knot spacing |p(i+1) - p(i)|^alpha (Barry and Goldman's pyramid of linear interpolations).
 */
export function catmullRomPoint(p0, p1, p2, p3, u, alpha = 0.5) {
  [p0, p1, p2, p3].forEach((point, index) => vector(point, `p${index}`));
  if (!(u >= 0 && u <= 1)) throw new RangeError(`u must be in [0, 1], got ${u}`);
  if (!(alpha >= 0 && alpha <= 1)) throw new RangeError(`alpha must be in [0, 1], got ${alpha}`);
  const t0 = 0;
  const t1 = knot(p0, p1, alpha);
  const t2 = t1 + knot(p1, p2, alpha);
  const t3 = t2 + knot(p2, p3, alpha);
  const t = t1 + (t2 - t1) * u;
  const point = [0, 0, 0];
  for (let k = 0; k < 3; k += 1) {
    const a1 = ((t1 - t) * p0[k] + (t - t0) * p1[k]) / (t1 - t0);
    const a2 = ((t2 - t) * p1[k] + (t - t1) * p2[k]) / (t2 - t1);
    const a3 = ((t3 - t) * p2[k] + (t - t2) * p3[k]) / (t3 - t2);
    const b1 = ((t2 - t) * a1 + (t - t0) * a2) / (t2 - t0);
    const b2 = ((t3 - t) * a2 + (t - t1) * a3) / (t3 - t1);
    point[k] = ((t2 - t) * b1 + (t - t1) * b2) / (t2 - t1);
  }
  return point;
}

function matrixQuaternion(x, y, z) {
  // Columns x, y and z of a rotation matrix to a unit quaternion (largest-component branch for stability).
  const [m00, m10, m20] = x;
  const [m01, m11, m21] = y;
  const [m02, m12, m22] = z;
  const trace = m00 + m11 + m22;
  let q;
  if (trace > 0) {
    const s = 0.5 / Math.sqrt(trace + 1);
    q = [(m21 - m12) * s, (m02 - m20) * s, (m10 - m01) * s, 0.25 / s];
  } else if (m00 > m11 && m00 > m22) {
    const s = 2 * Math.sqrt(1 + m00 - m11 - m22);
    q = [0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s];
  } else if (m11 > m22) {
    const s = 2 * Math.sqrt(1 + m11 - m00 - m22);
    q = [(m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s];
  } else {
    const s = 2 * Math.sqrt(1 + m22 - m00 - m11);
    q = [(m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s];
  }
  const norm = Math.hypot(q[0], q[1], q[2], q[3]);
  return q.map((value) => value / norm);
}

/**
 * The orientation of a camera at `position` looking at `target` with `up` as near to its up axis as possible: the
 * camera's -Z axis points at the target. When the view is parallel to up, the world Z axis (or X) stands in for up.
 */
export function lookRotation(position, target, up = [0, 1, 0]) {
  vector(position, 'position');
  vector(target, 'target');
  vector(up, 'up');
  const back = subtract(position, target);
  const distance = length(back);
  if (!(distance > 0)) throw new RangeError('position and target are the same point');
  const z = scale(back, 1 / distance);
  let right = cross(up, z);
  for (const fallback of [[0, 0, 1], [1, 0, 0]]) {
    if (length(right) > NEAR_PARALLEL) break;
    right = cross(fallback, z);
  }
  const x = scale(right, 1 / length(right));
  const y = cross(z, x);
  return matrixQuaternion(x, y, z);
}

/** Spherical linear interpolation between unit quaternions along the shorter arc. */
export function slerpQuaternion(a, b, u) {
  vector(a, 'a', 4);
  vector(b, 'b', 4);
  if (!(u >= 0 && u <= 1)) throw new RangeError(`u must be in [0, 1], got ${u}`);
  let dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
  const end = dot < 0 ? b.map((value) => -value) : b;
  dot = Math.abs(dot);
  let wa = 1 - u;
  let wb = u;
  if (dot < 0.9995) {
    const angle = Math.acos(Math.min(dot, 1));
    const sine = Math.sin(angle);
    wa = Math.sin((1 - u) * angle) / sine;
    wb = Math.sin(u * angle) / sine;
  }
  const q = a.map((value, index) => wa * value + wb * end[index]);
  const norm = Math.hypot(q[0], q[1], q[2], q[3]);
  return q.map((value) => value / norm);
}

/** The timeline easing: linear, smoothstep (3t^2 - 2t^3) or smootherstep (6t^5 - 15t^4 + 10t^3), t in [0, 1]. */
export function easeTime(t, easing = 'smoothstep') {
  if (!EASINGS.has(easing)) throw new TypeError(`easing must be one of ${[...EASINGS].join(', ')}`);
  if (!Number.isFinite(t)) throw new RangeError(`t must be finite, got ${t}`);
  const x = Math.min(Math.max(t, 0), 1);
  if (easing === 'smoothstep') return x * x * (3 - 2 * x);
  if (easing === 'smootherstep') return x * x * x * (x * (x * 6 - 15) + 10);
  return x;
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(CINEMATIC_PATH_DEFAULTS, key)) throw new TypeError(`unknown camera path option ${key}`);
  }
  const settings = {...CINEMATIC_PATH_DEFAULTS, ...options};
  if (!(settings.alpha >= 0 && settings.alpha <= 1)) throw new RangeError('alpha must be in [0, 1]');
  if (typeof settings.closed !== 'boolean') throw new TypeError('closed must be true or false');
  if (!(Number.isInteger(settings.samplesPerSegment) && settings.samplesPerSegment >= 4
    && settings.samplesPerSegment <= 4096)) {
    throw new RangeError('samplesPerSegment must be an integer from 4 to 4096');
  }
  if (!EASINGS.has(settings.easing)) throw new TypeError(`easing must be one of ${[...EASINGS].join(', ')}`);
  vector(settings.up, 'up');
  return settings;
}

/**
 * A camera path through keyframes {position, target?, quaternion?}. Every keyframe has a target (the camera looks
 * at the interpolated target), or every keyframe has a quaternion (slerped), or none has either (the camera looks
 * along its direction of travel). sampleAt(t) for t in [0, 1] moves at constant speed along the arc length of the
 * eased timeline; applyTo(camera, t) poses a three.js camera.
 */
export class CameraPath {
  constructor(keyframes, options = {}) {
    this.settings = settingsOf(options);
    if (!Array.isArray(keyframes) || keyframes.length < 2) throw new TypeError('keyframes must be at least two keyframes');
    const withTarget = keyframes.filter((frame) => frame && frame.target !== undefined).length;
    const withQuaternion = keyframes.filter((frame) => frame && frame.quaternion !== undefined).length;
    if ((withTarget && withTarget !== keyframes.length) || (withQuaternion && withQuaternion !== keyframes.length)
      || (withTarget && withQuaternion)) {
      throw new TypeError('every keyframe has a target, or every keyframe has a quaternion, or none has either');
    }
    this.mode = withTarget ? 'target' : withQuaternion ? 'quaternion' : 'tangent';
    this.positions = keyframes.map((frame, index) => [...vector(frame.position, `keyframes[${index}].position`)]);
    this.targets = withTarget ? keyframes.map((frame, index) => [...vector(frame.target, `keyframes[${index}].target`)]) : null;
    this.quaternions = withQuaternion ? keyframes.map((frame, index) => {
      const q = vector(frame.quaternion, `keyframes[${index}].quaternion`, 4);
      const norm = Math.hypot(q[0], q[1], q[2], q[3]);
      if (!(norm > 0)) throw new RangeError(`keyframes[${index}].quaternion is zero`);
      return q.map((value) => value / norm);
    }) : null;
    const count = this.positions.length;
    this.segments = this.settings.closed ? count : count - 1;
    for (let segment = 0; segment < this.segments; segment += 1) {
      const next = (segment + 1) % count;
      if (length(subtract(this.positions[next], this.positions[segment])) === 0) {
        throw new RangeError(`keyframes ${segment} and ${next} share a position`);
      }
    }
    const steps = this.settings.samplesPerSegment;
    this.table = new Float64Array(this.segments * steps + 1);
    let previous = this.pointOnSegment(0, 0);
    for (let segment = 0; segment < this.segments; segment += 1) {
      for (let step = 1; step <= steps; step += 1) {
        const point = this.pointOnSegment(segment, step / steps);
        const index = segment * steps + step;
        this.table[index] = this.table[index - 1] + length(subtract(point, previous));
        previous = point;
      }
    }
    this.length = this.table[this.table.length - 1];
  }

  controlPoints(points, segment) {
    const count = points.length;
    const p1 = points[segment];
    const p2 = points[(segment + 1) % count];
    let p0;
    let p3;
    if (this.settings.closed) {
      p0 = points[(segment - 1 + count) % count];
      p3 = points[(segment + 2) % count];
    } else {
      p0 = segment > 0 ? points[segment - 1] : subtract(scale(p1, 2), p2);
      p3 = segment + 2 < count ? points[segment + 2] : subtract(scale(p2, 2), p1);
    }
    return [p0, p1, p2, p3];
  }

  pointOnSegment(segment, u) {
    const [p0, p1, p2, p3] = this.controlPoints(this.positions, segment);
    return catmullRomPoint(p0, p1, p2, p3, u, this.settings.alpha);
  }

  /** {segment, u} at an arc-length distance from the start (clamped to the path). */
  locate(distance) {
    const steps = this.settings.samplesPerSegment;
    const clamped = Math.min(Math.max(distance, 0), this.length);
    let low = 0;
    let high = this.table.length - 1;
    while (high - low > 1) {
      const middle = (low + high) >> 1;
      if (this.table[middle] <= clamped) low = middle;
      else high = middle;
    }
    const span = this.table[high] - this.table[low];
    const fraction = span > 0 ? (clamped - this.table[low]) / span : 0;
    const position = low + fraction;
    const segment = Math.min(Math.floor(position / steps), this.segments - 1);
    return {segment, u: Math.min((position - segment * steps) / steps, 1)};
  }

  pointAtDistance(distance) {
    const {segment, u} = this.locate(distance);
    return this.pointOnSegment(segment, u);
  }

  /** Arc-length fractions in [0, 1] where the path passes each keyframe (before easing). */
  keyframeFractions() {
    const steps = this.settings.samplesPerSegment;
    const fractions = [];
    for (let segment = 0; segment <= this.segments; segment += 1) fractions.push(this.table[segment * steps] / this.length);
    return fractions;
  }

  orientation(segment, u, position) {
    if (this.mode === 'target') {
      const [t0, t1, t2, t3] = this.controlPoints(this.targets, segment);
      return lookRotation(position, catmullRomPoint(t0, t1, t2, t3, u, this.settings.alpha), this.settings.up);
    }
    if (this.mode === 'quaternion') {
      const count = this.quaternions.length;
      return slerpQuaternion(this.quaternions[segment], this.quaternions[(segment + 1) % count], u);
    }
    const ahead = this.pointOnSegment(segment, Math.min(u + 1e-3, 1));
    const behind = this.pointOnSegment(segment, Math.max(u - 1e-3, 0));
    return lookRotation(behind, ahead, this.settings.up);
  }

  /** The camera at timeline t in [0, 1]: {position, quaternion, distance, segment, u}. */
  sampleAt(t) {
    const eased = easeTime(t, this.settings.easing);
    const distance = eased * this.length;
    const {segment, u} = this.locate(distance);
    const position = this.pointOnSegment(segment, u);
    return {position, quaternion: this.orientation(segment, u, position), distance, segment, u};
  }

  /** Pose a three.js camera (any object with position.set and quaternion.set) at timeline t. */
  applyTo(camera, t) {
    const {position, quaternion} = this.sampleAt(t);
    camera.position.set(position[0], position[1], position[2]);
    camera.quaternion.set(quaternion[0], quaternion[1], quaternion[2], quaternion[3]);
    return camera;
  }
}
