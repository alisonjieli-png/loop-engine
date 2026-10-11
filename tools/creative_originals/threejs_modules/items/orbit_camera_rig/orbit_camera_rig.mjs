// An orbit camera rig for three.js that is independent of input devices: a target, a radius and two angles (azimuth
// about +Y, polar from +Y), each with a goal the current value reaches by exact exponential smoothing, so the motion
// is the same at any frame rate. Rotate, dolly and pan change the goals (pan moves in the view plane, scaled by the
// distance), limits clamp them, and applyTo places a three.js camera. Original Baltor implementation.

/** Default options of OrbitCameraRig. Angles are radians; smoothTime 0 snaps to every goal. */
export const ORBIT_RIG_DEFAULTS = Object.freeze({
  target: Object.freeze([0, 0, 0]),
  radius: 5,
  azimuth: 0,
  polar: Math.PI / 3,
  minRadius: 0.5,
  maxRadius: 100,
  minPolar: 0.05,
  maxPolar: Math.PI - 0.05,
  smoothTime: 0.12,
});

const SETTLED = 1e-9;

function clamp(value, low, high) {
  return Math.min(Math.max(value, low), high);
}

function finite(value, name) {
  if (!(typeof value === 'number' && Number.isFinite(value))) throw new RangeError(`${name} must be a finite number`);
  return value;
}

/** The point at radius and angles around target, with three.js's spherical convention (polar from +Y). */
export function orbitPosition(target, radius, azimuth, polar) {
  const ring = radius * Math.sin(polar);
  return [target[0] + ring * Math.sin(azimuth), target[1] + radius * Math.cos(polar), target[2] + ring * Math.cos(azimuth)];
}

/** {radius, azimuth, polar} of a position around a target (the inverse of orbitPosition). */
export function orbitAngles(position, target) {
  const dx = position[0] - target[0];
  const dy = position[1] - target[1];
  const dz = position[2] - target[2];
  const radius = Math.hypot(dx, dy, dz);
  if (!(radius > 0)) throw new RangeError('the position and the target are the same point');
  return {radius, azimuth: Math.atan2(dx, dz), polar: Math.acos(clamp(dy / radius, -1, 1))};
}

/**
 * The rig. rotate(deltaAzimuth, deltaPolar), dolly(factor), pan(dx, dy) (in radius units along the view's right and
 * up) and panPixels(dx, dy, fovDegrees, viewportHeight) change the goal; update(dt) moves the current state toward
 * it and returns whether it is still moving; applyTo(camera) places a three.js camera.
 */
export class OrbitCameraRig {
  constructor(options = {}) {
    for (const key of Object.keys(options)) {
      if (!Object.prototype.hasOwnProperty.call(ORBIT_RIG_DEFAULTS, key)) throw new TypeError(`unknown orbit rig option ${key}`);
    }
    const settings = {...ORBIT_RIG_DEFAULTS, ...options};
    for (const key of ['radius', 'azimuth', 'polar', 'minRadius', 'maxRadius', 'minPolar', 'maxPolar', 'smoothTime']) {
      finite(settings[key], key);
    }
    if (!(settings.minRadius > 0 && settings.minRadius <= settings.maxRadius)) {
      throw new RangeError('radius limits need 0 < minRadius <= maxRadius');
    }
    if (!(settings.minPolar >= 0 && settings.minPolar <= settings.maxPolar && settings.maxPolar <= Math.PI)) {
      throw new RangeError('polar limits need 0 <= minPolar <= maxPolar <= pi');
    }
    if (!(settings.smoothTime >= 0)) throw new RangeError('smoothTime must be zero or positive');
    if (!(settings.target && settings.target.length === 3)) throw new RangeError('target must be three numbers');
    this.limits = {minRadius: settings.minRadius, maxRadius: settings.maxRadius, minPolar: settings.minPolar,
      maxPolar: settings.maxPolar};
    this.smoothTime = settings.smoothTime;
    const start = {
      target: settings.target.map((value, axis) => finite(value, `target[${axis}]`)),
      radius: clamp(settings.radius, settings.minRadius, settings.maxRadius),
      azimuth: settings.azimuth,
      polar: clamp(settings.polar, settings.minPolar, settings.maxPolar),
    };
    this.current = {...start, target: [...start.target]};
    this.goal = {...start, target: [...start.target]};
  }

  rotate(deltaAzimuth, deltaPolar) {
    this.goal.azimuth += finite(deltaAzimuth, 'deltaAzimuth');
    this.goal.polar = clamp(this.goal.polar + finite(deltaPolar, 'deltaPolar'), this.limits.minPolar, this.limits.maxPolar);
    return this;
  }

  dolly(factor) {
    if (!(factor > 0 && Number.isFinite(factor))) throw new RangeError('the dolly factor must be positive');
    this.goal.radius = clamp(this.goal.radius * factor, this.limits.minRadius, this.limits.maxRadius);
    return this;
  }

  pan(dx, dy) {
    finite(dx, 'dx');
    finite(dy, 'dy');
    const {azimuth, polar, radius} = this.goal;
    const right = [Math.cos(azimuth), 0, -Math.sin(azimuth)];
    const up = [-Math.sin(azimuth) * Math.cos(polar), Math.sin(polar), -Math.cos(azimuth) * Math.cos(polar)];
    for (let axis = 0; axis < 3; axis += 1) this.goal.target[axis] += (right[axis] * dx + up[axis] * dy) * radius;
    return this;
  }

  panPixels(dx, dy, fovDegrees, viewportHeight) {
    if (!(fovDegrees > 0 && fovDegrees < 180 && viewportHeight > 0)) {
      throw new RangeError('panPixels needs a field of view in (0, 180) and a positive viewport height');
    }
    // One pixel covers 2 tan(fov / 2) / height radius units at the target's distance; moving the target against the
    // pointer keeps the point under the pointer in place.
    const unit = (2 * Math.tan((fovDegrees * Math.PI) / 360)) / viewportHeight;
    return this.pan(-dx * unit, dy * unit);
  }

  setFromPosition(position, target) {
    const angles = orbitAngles(position, target);
    const state = {
      target: [...target],
      radius: clamp(angles.radius, this.limits.minRadius, this.limits.maxRadius),
      azimuth: angles.azimuth,
      polar: clamp(angles.polar, this.limits.minPolar, this.limits.maxPolar),
    };
    this.current = {...state, target: [...state.target]};
    this.goal = {...state, target: [...state.target]};
    return this;
  }

  snap() {
    this.current = {...this.goal, target: [...this.goal.target]};
    return this;
  }

  update(dt) {
    if (!(dt >= 0 && Number.isFinite(dt))) throw new RangeError('dt must be zero or positive');
    const keep = this.smoothTime > 0 ? Math.exp(-dt / this.smoothTime) : 0;
    let moving = false;
    const approach = (current, goal) => {
      const next = goal + (current - goal) * keep;
      if (Math.abs(next - goal) > SETTLED * Math.max(1, Math.abs(goal))) moving = true;
      return next;
    };
    for (const key of ['radius', 'azimuth', 'polar']) this.current[key] = approach(this.current[key], this.goal[key]);
    for (let axis = 0; axis < 3; axis += 1) {
      this.current.target[axis] = approach(this.current.target[axis], this.goal.target[axis]);
    }
    return moving;
  }

  position() {
    const {target, radius, azimuth, polar} = this.current;
    return orbitPosition(target, radius, azimuth, polar);
  }

  applyTo(camera) {
    const [x, y, z] = this.position();
    camera.position.set(x, y, z);
    camera.up.set(0, 1, 0);
    camera.lookAt(this.current.target[0], this.current.target[1], this.current.target[2]);
    return camera;
  }
}
