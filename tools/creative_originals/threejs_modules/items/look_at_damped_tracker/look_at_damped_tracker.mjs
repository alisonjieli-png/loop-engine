// Damped look-at tracking for turrets, heads, eyes and spotlights: aim an object's +Z axis at a target through yaw
// about its rest up axis and pitch about its yawed side axis, clamp both to limits around the rest orientation, and
// approach the aim with exponential smoothing and a cap on the angle turned per second. Original Baltor
// implementation; quaternions are [x, y, z, w], vectors [x, y, z], time is passed in, nothing is imported.

/** Default options. Angles are radians; maxSpeed caps |yaw step| + |pitch step| per second. */
export const LOOK_TRACKER_DEFAULTS = Object.freeze({
  maxSpeed: 3,
  smoothing: 0.12,
  yawLimit: Math.PI,
  pitchMin: -0.6,
  pitchMax: 1.0,
});

function vector(value, name, size = 3) {
  if (!(Array.isArray(value) && value.length === size && value.every(Number.isFinite))) {
    throw new TypeError(`${name} must be ${size} finite numbers`);
  }
  return value;
}

function multiply(a, b) {
  return [
    a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
    a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
    a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
    a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
  ];
}

function rotate(q, v) {
  const p = multiply(multiply(q, [v[0], v[1], v[2], 0]), [-q[0], -q[1], -q[2], q[3]]);
  return [p[0], p[1], p[2]];
}

function unit(q) {
  const norm = Math.hypot(q[0], q[1], q[2], q[3]);
  if (!(norm > 0)) throw new RangeError('the rest quaternion is zero');
  return q.map((value) => value / norm);
}

function wrap(angle) {
  const turned = angle - 2 * Math.PI * Math.floor((angle + Math.PI) / (2 * Math.PI));
  return turned === -Math.PI ? Math.PI : turned;
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(LOOK_TRACKER_DEFAULTS, key)) throw new TypeError(`unknown look tracker option ${key}`);
  }
  const settings = {...LOOK_TRACKER_DEFAULTS, ...options};
  if (!(settings.maxSpeed > 0 && Number.isFinite(settings.maxSpeed))) throw new RangeError('maxSpeed must be positive');
  if (!(settings.smoothing >= 0 && settings.smoothing <= 60)) throw new RangeError('smoothing must be in [0, 60] seconds');
  if (!(settings.yawLimit >= 0 && settings.yawLimit <= Math.PI)) throw new RangeError('yawLimit must be in [0, pi]');
  if (!(settings.pitchMin >= -Math.PI / 2 && settings.pitchMax <= Math.PI / 2 && settings.pitchMin <= settings.pitchMax)) {
    throw new RangeError('pitch limits must satisfy -pi/2 <= pitchMin <= pitchMax <= pi/2');
  }
  return settings;
}

/**
 * The unclamped aim {yaw, pitch} toward `target` from `position` for an object whose rest orientation is
 * `restQuaternion` (all in the same frame, usually the object's parent): yaw turns the rest +Z axis about the rest
 * +Y axis toward +X, pitch lifts it toward +Y.
 */
export function aimAngles(restQuaternion, position, target) {
  const rest = unit(vector(restQuaternion, 'restQuaternion', 4));
  vector(position, 'position');
  vector(target, 'target');
  const direction = [target[0] - position[0], target[1] - position[1], target[2] - position[2]];
  if (!(Math.hypot(...direction) > 0)) throw new RangeError('position and target are the same point');
  const local = rotate([-rest[0], -rest[1], -rest[2], rest[3]], direction);
  return {yaw: Math.atan2(local[0], local[2]), pitch: Math.atan2(local[1], Math.hypot(local[0], local[2]))};
}

/** The aim clamped to the yaw and pitch limits; clamped tells whether either angle was limited. */
export function clampAim(angles, options = {}) {
  const settings = settingsOf(options);
  const yaw = Math.min(Math.max(angles.yaw, -settings.yawLimit), settings.yawLimit);
  const pitch = Math.min(Math.max(angles.pitch, settings.pitchMin), settings.pitchMax);
  return {yaw, pitch, clamped: yaw !== angles.yaw || pitch !== angles.pitch};
}

/** The orientation for yaw and pitch around the rest orientation: rest, then yaw about +Y, then pitch about +X. */
export function orientationFromAngles(restQuaternion, yaw, pitch) {
  const rest = unit(vector(restQuaternion, 'restQuaternion', 4));
  if (!(Number.isFinite(yaw) && Number.isFinite(pitch))) throw new RangeError('yaw and pitch must be finite');
  const turn = [0, Math.sin(yaw / 2), 0, Math.cos(yaw / 2)];
  const lift = [Math.sin(-pitch / 2), 0, 0, Math.cos(-pitch / 2)];
  return multiply(multiply(rest, turn), lift);
}

/**
 * One update from `current` toward `goal` ({yaw, pitch}) over deltaSeconds: an exponential approach with time
 * constant `smoothing`, then the step is scaled so |yaw step| + |pitch step| <= maxSpeed * deltaSeconds, which bounds
 * the angle actually turned. With yawLimit = pi the yaw takes the shorter way round.
 */
export function stepAngles(current, goal, deltaSeconds, options = {}) {
  const settings = settingsOf(options);
  if (!(Number.isFinite(deltaSeconds) && deltaSeconds >= 0)) throw new RangeError('deltaSeconds must be non-negative');
  const unlimited = settings.yawLimit >= Math.PI;
  const yawGap = unlimited ? wrap(goal.yaw - current.yaw) : goal.yaw - current.yaw;
  const pitchGap = goal.pitch - current.pitch;
  const fraction = settings.smoothing > 0 ? 1 - Math.exp(-deltaSeconds / settings.smoothing) : 1;
  let yawStep = yawGap * fraction;
  let pitchStep = pitchGap * fraction;
  const budget = settings.maxSpeed * deltaSeconds;
  const wanted = Math.abs(yawStep) + Math.abs(pitchStep);
  if (wanted > budget) {
    yawStep *= budget / wanted;
    pitchStep *= budget / wanted;
  }
  const yaw = current.yaw + yawStep;
  return {yaw: unlimited ? wrap(yaw) : yaw, pitch: current.pitch + pitchStep};
}

/**
 * A tracker that keeps its own yaw and pitch. update(position, target, deltaSeconds) turns toward the clamped aim
 * and returns {yaw, pitch, quaternion, clamped}; applyTo(object) writes the orientation into object.quaternion
 * (position, target and the rest orientation are in the object's parent frame).
 */
export class LookAtTracker {
  constructor(options = {}, restQuaternion = [0, 0, 0, 1]) {
    this.settings = settingsOf(options);
    this.rest = unit(vector(restQuaternion, 'restQuaternion', 4));
    this.yaw = 0;
    this.pitch = 0;
  }

  get quaternion() {
    return orientationFromAngles(this.rest, this.yaw, this.pitch);
  }

  update(position, target, deltaSeconds) {
    const goal = clampAim(aimAngles(this.rest, position, target), this.settings);
    const next = stepAngles(this, goal, deltaSeconds, this.settings);
    this.yaw = next.yaw;
    this.pitch = next.pitch;
    return {yaw: this.yaw, pitch: this.pitch, quaternion: this.quaternion, clamped: goal.clamped};
  }

  applyTo(object) {
    const q = this.quaternion;
    object.quaternion.set(q[0], q[1], q[2], q[3]);
    return object;
  }
}
